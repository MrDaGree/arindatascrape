import requests
from bs4 import BeautifulSoup
import argparse
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

#inital beautfulsoup query on search to get list of addition "customers" as well.
request = {
    'queryinput': args.search 
}
page = requests.post('https://whois.arin.net/ui/query.do', data=request)
soup = BeautifulSoup(page.text, 'html.parser')
querycontent = soup.find('div', {"id": "maincontent"})
tablerows = querycontent.find('table').find_all("tr")

#customer link counter in case user only wants to do a certain few
customer_link_check = 0

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
                #check if user only wanted to scrape a few customers or all
                if args.limit:
                    #check if we are at the user supplied customer check limit
                    if (customer_link_check < args.limit):
                        customer_link_check += 1
                        #parse the customer data as an XML
                        customer_soup = BeautifulSoup(requests.get(customer_link).text, 'xml')
                        netref = customer_soup.find('netRef')
                        addr = netref['startAddress'] + " - " + netref['endAddress']
                        #append the IP address of the customer to the known IP addresses
                        known_ip_addresses.append(addr)
                else:
                    #parse the customer data as an XML
                    customer_soup = BeautifulSoup(requests.get(customer_link).text, 'xml')
                    netref = customer_soup.find('netRef')
                    addr = netref['startAddress'] + " - " + netref['endAddress']
                    #append the IP address of the customer to the known IP addresses
                    known_ip_addresses.append(addr)

print("-" * 64)
print("\tArin IP address scraper by MrDaGree")
print("\nSearch Queried: " + args.search)
if args.limit:
    print("Search Sub-Customer Limit: " + str(args.limit))
else:
    print("Search Sub-Customer Limit: ALL")
print("\nKnown IP Addresses:")
for ip in known_ip_addresses:
    print(ip)
print("-" * 64)