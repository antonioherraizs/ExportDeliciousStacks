#!/usr/bin/env python3
"""
Exports stacks from a Delicious account.

Features:
1. Exports to a JSON file.
2. Modifies an existing bookmarks file in Netscape Bookmarks File Format to add stack info to known links.
3. Generates a new bookmarks file in NBFF with stacks.

Usage: [delicious_username] [deli‭cious_password] [bookmarks file]

History:
v1.0 - First release

TODO:
- make features optional, based in CL choice
- in feature 2, handle same links appearing in > 1 stack
- explore http vs https results: stack links page doesn't use https 
- exceptions, validation.

Antonio Herraiz 4 www.toniblogs.com
"""

from http import cookiejar
from urllib import request, parse
from bs4 import BeautifulSoup # get it from http://www.crummy.com/software/BeautifulSoup/
from time import sleep
from json import dumps
from sys import argv

username = argv[1]
password = argv[2]
exp_bookmarks_file = argv[3][:-5] # expect .html file

cj = cookiejar.CookieJar()
opener = request.build_opener(request.HTTPCookieProcessor(cj))
login_data = parse.urlencode({'username' : username, 'password' : password})

opener.open('https://delicious.com/login', login_data.encode('ascii'))

resp = opener.open('https://delicious.com/stacks/' + username)
soup = BeautifulSoup(resp.read())

# we're in the first page, take links from here first
stack_links = soup.find_all('a', 'stackLink')

# and add links from rest of pages, if any
for page_link in soup.find_all('div', id='pagination'):
    next_page = 'https://delicious.com/stacks/' + username + page_link.a['href']
    next = opener.open(next_page)
    soup2 = BeautifulSoup(next.read())
    stack_links += soup2.find_all('a', 'stackLink')

# for each stack link
# visit stack page in list mode (delicious.com/stacks/view/[StackCode]?m=list)
# store stack_name, stack_id (6 digits)
# simulate XMLHttpRequest to get list of links from the stack:
# GET /stacks/fragment/elements/[stack_id]?mode=list&editor=[username]&search=&editMode=false
# go through the links in the stack, taking link_href, link_title
# store everything for further processing
stack_base_url = 'https://delicious.com'
stacks = []
stack_num = 1
num_links = 0
for stack_link in stack_links:
    stack_page = stack_base_url + stack_link['href'] + '?m=list'
    page = opener.open(stack_page)
    page_soup = BeautifulSoup( page.read() )
    stack = {}
    stack['name'] = page_soup.find('input', { 'id' : 'stackTitleInlineEdit' } )['value']
    stack['id'] = page_soup.find('input', { 'id' : 'stack_view_stack_id' } )['value']
    stack['stack_link'] = stack_page
    stack['links'] = []
    stack_links_page = stack_base_url + '/stacks/fragment/elements/' + stack['id'] + '?mode=list&editor=' + username + '&search=&editMode=false'
    page = opener.open(stack_links_page)
    page_soup = BeautifulSoup( page.read() )
    for link in page_soup.find_all('div', 'action share'):
        stack['links'].append( {'href' : link['href'], 'title' : link['title']} )
        num_links += 1
    stacks.append(stack)
    print( 'extracting stack {0} ({1}/{2}). {3} links in all stacks'.format(stack_link['href'][-6:], stack_num, len(stack_links), num_links) )
    stack_num += 1
    sleep(0.5) # be easy on servers

#
# export to JSON
#
f = open(exp_bookmarks_file + '.json', 'w')
f.write( dumps(stacks) )
f.close()

#
# make new version of exported bookmarks file by adding stack details to each link
# it doesn't deal with ‌links present in > 1 stack 
#
f = open(exp_bookmarks_file + '.html')
delicious = BeautifulSoup(f.read())

for stack in stacks:
    for link in stack['links']:
        a = delicious.find(href = link['href'])
        a['stack_id'] = stack['id']
        a['stack_name'] = stack['name']

f = open(exp_bookmarks_file + '-with-stack-info.html', 'w')
f.write( str(delicious) )
f.close()

#
# export stacks to a Netscape Bookmark File Format: http://msdn.microsoft.com/en-us/library/aa753582(v=vs.85).aspx
#
head = """
<!DOCTYPE NETSCAPE-Bookmark-file-1>
<!-- This is an automatically generated file.
     It will be read and overwritten.
     DO NOT EDIT! -->
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks Menu</H1>

"""

tmp = BeautifulSoup("") # just to create some HTML tags
start = '<DL><p>\n'
end = '</DL><p>\n'
tab = '    '

html_stacks = head + start

for stack in stacks:
    h3 = tmp.new_tag('H3') # chrome needs the 'h' to be uppercase!
    h3.string = stack['name']
    s = tab + '<DT>' + str(h3) + '\n'
    html_stacks += s + tab + start
    for link in stack['links']:
        a = tmp.new_tag('a', href = link['href'])
        a.string = link['title']
        l = 2 * tab + '<DT>' + str(a) + '\n'
        html_stacks += l
    html_stacks += tab + end

html_stacks += end

f = open(exp_bookmarks_file + '-only-stacks.html', 'w')
f.write(html_stacks)
f.close()

# EOF
