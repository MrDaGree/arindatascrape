import sys
import time
import argparse
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

#setup runtime terminal arguments
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--search", type=str, help="Search query string for Arin")
parser.add_argument("-l", "--limit", type=int, help="Limit of additional \"sub\" customers to search in")
args = parser.parse_args()

#quit if there is no search string
if not args.search:
    exit()

#list of known addresses after the scrape to then output for user
known_ip_addresses = []

def progress(count, total, status='', bar_len=60):
    filled_len = int(round(bar_len * count / float(total)))

    percents = str(count) + " / " + str(total)
    bar = '█' * filled_len + '-' * (bar_len - filled_len)

    fmt = '%s [%s] %s' % (status, bar, percents,)
    print('\b' * len(fmt), end='')  # clears the line
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
                    count += 1

    if args.limit: 
        if args.limit < count:
            count = args.limit

    return count

def customerScrape(link):
    customer_soup = BeautifulSoup(requests.get(link).text, 'xml')
    netref = customer_soup.find('netRef')
    addr = netref['startAddress'] + " - " + netref['endAddress'] + " | Customer ID: " + customer_soup.find('handle').text

    known_ip_addresses.append(addr)

#start time
start_time = time.perf_counter()

if "C0" in args.search:
    #append the IP address of the customer to the known IP addresses
    known_ip_addresses.append(customerScrape("https://whois.arin.net/rest/customer/" + args.search))
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
                known_ip_addresses.append(cells[1].text)
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
print("-" * 64)
print("\tArin IP address scraper by MrDaGree")
print("\nSearch Queried: " + args.search)
print("\nSearch Time: " + str(search_time))
print("\nKnown IP Addresses:")
for ip in known_ip_addresses:
    print(ip)
print("-" * 64)