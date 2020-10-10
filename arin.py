import sys
import time
import argparse
import requests
import netaddr
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

#setup runtime terminal arguments
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--search", type=str, help="Search query string for Arin")
parser.add_argument("-l", "--limit", type=int, help="Limit of additional \"sub\" customers to search in")
parser.add_argument("-sB", "--sortbig", help="Sort from biggest net size to smallest", action='store_true')
parser.add_argument("-sS", "--sortsmall", help="Sort from smallest net size to biggest", action='store_true')
args = parser.parse_args()

#quit if there is no search string
if not args.search:
    exit()

#list of known addresses after the scrape to then output for user
known_ip_addresses = {}


#progress bar modified from user 'MarcDirven' from https://gist.github.com/vladignatyev/06860ec2040cb497f0f3#gistcomment-3133443
def progress(count, total, status='', bar_len=60):
    filled_len = int(round(bar_len * count / float(total)))

    percents = str(count) + " / " + str(total)
    bar = '█' * filled_len + '-' * (bar_len - filled_len)

    fmt = '%s [%s] %s' % (status, bar, percents,)
    print('\b' * len(fmt), end='')
    sys.stdout.write(fmt)
    sys.stdout.flush()

def countCustomers(tablerows):
    count = 0

    for row in tablerows:
        cells = row.find_all("td")
        if cells:
            #if the cell has a length of less than 2 is the customer link on main page.
            if len(cells) < 2:
                #get customer link from table cell
                customer_link = cells[0].find('a').get('href')
                #ensure the link found is a customer link, sometimes org links and those arent helpful in this case
                if "https://whois.arin.net/rest/customer/" in customer_link:
                    #add one to count each time new customer link is discovered.
                    count += 1

    #check if user defined a limit
    if args.limit: 
        #if the limit is less than the total customer count then set count to limit
        if args.limit < count:
            count = args.limit
    
    return count

def customerScrape(link):
    customer_soup = BeautifulSoup(requests.get(link).text, 'xml')
    netref = customer_soup.find('netRef')

    cidrs = netaddr.iprange_to_cidrs(netref['startAddress'], netref['endAddress'])
    size = int(str(cidrs[0]).split("/")[1])

    data = {
        'startIP': netref['startAddress'],
        'endIP': netref['endAddress'],
        'rangeSize': size,
        'range': str(cidrs[0]),
        'customerID': customer_soup.find('handle').text
    }

    known_ip_addresses[len(known_ip_addresses) + 1] = data

#start time
start_time = time.perf_counter()

if "C0" in args.search:
    #append the IP address of the customer to the known IP addresses
    customerScrape("https://whois.arin.net/rest/customer/" + args.search)
else:
    #inital beautfulsoup query on search to get list of addition "customers" as well.
    request = {
        'queryinput': args.search 
    }
    page = requests.post('https://whois.arin.net/ui/query.do', data=request)
    soup = BeautifulSoup(page.text, 'html.parser')
    querycontent = soup.find('div', {"id": "maincontent"})
    tablerows = querycontent.find('table').find_all("tr")

    #customer link counter for progress bar
    customer_link_check = 0
    #total customers returned from 'countCustomers' function which either scrapes total customers off main page or returns the user limit
    total_customers = countCustomers(tablerows)

    #loop through main page table
    for row in tablerows:
        cells = row.find_all("td")
        if cells:
            #if the cell has a length of 2 it includes an IP address in the table on main page
            if len(cells) == 2:
                ip_range = cells[1].text.split(' ')
                cidrs = netaddr.iprange_to_cidrs(ip_range[0], ip_range[2])
                size = int(str(cidrs[0]).split("/")[1])

                data = {
                    'startIP': ip_range[0],
                    'endIP': ip_range[2],
                    'rangeSize': size,
                    'range': str(cidrs[0])
                }

                known_ip_addresses[len(known_ip_addresses) + 1] = data
            #the cell length isnt 2 so it has to be a customer ID with link
            else:
                #get customer link from table cell
                customer_link = cells[0].find('a').get('href')
                #ensure the link found is a customer link, sometimes org links and those arent helpful in this case
                if "https://whois.arin.net/rest/customer/" in customer_link:
                    #check if count is less than total
                    if customer_link_check < total_customers:
                        customer_link_check += 1
                        progress(customer_link_check, total_customers, "Customers Check")
                        customerScrape(customer_link)


search_time = time.perf_counter() - start_time        

print("\n\n")
print("-" * 110)
print("\tArin IP address scraper by MrDaGree")
print("\nSearch Queried: " + args.search)
print("\nSearch Time: " + str(search_time))
print("")
print ("{:<64} {:<25} {:<25}".format('IP RANGE', 'SIZE', 'CUSTOMER ID')) 
if args.sortbig:
    sorted_IPs = {}
    sorted_IPs = sorted(known_ip_addresses.items(), key=lambda k_v: k_v[1]['rangeSize'], reverse=True)
    for data in sorted_IPs:
        if 'customerID' in data[1]:
            ip_range = data[1]['startIP'] + " - " + data[1]['endIP']
            print ("{:<64} {:<25} {:<25}".format(ip_range, data[1]['range'], data[1]['customerID']))
        else:
            ip_range = data[1]['startIP'] + " - " + data[1]['endIP']
            print ("{:<64} {:<25}".format(ip_range, data[1]['range']))
elif args.sortsmall:
    sorted_IPs = {}
    sorted_IPs = sorted(known_ip_addresses.items(), key=lambda k_v: k_v[1]['rangeSize'])
    for data in sorted_IPs:
        if 'customerID' in data[1]:
            ip_range = data[1]['startIP'] + " - " + data[1]['endIP']
            print ("{:<64} {:<25} {:<25}".format(ip_range, data[1]['range'], data[1]['customerID']))
        else:
            ip_range = data[1]['startIP'] + " - " + data[1]['endIP']
            print ("{:<64} {:<25}".format(ip_range, data[1]['range']))
else:
    for data in known_ip_addresses.items():
        if 'customerID' in data[1]:
            ip_range = data[1]['startIP'] + " - " + data[1]['endIP']
            print ("{:<64} {:<25} {:<25}".format(ip_range, data[1]['range'], data[1]['customerID']))
        else:
            ip_range = data[1]['startIP'] + " - " + data[1]['endIP']
            print ("{:<64} {:<25}".format(ip_range, data[1]['range']))


print("-" * 110)