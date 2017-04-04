#!/usr/bin/python
#coding:utf-8

from bs4 import BeautifulSoup
import requests
import re
TestUrl='https://zh.wikipedia.org/wiki/范冰冰'


# def getHtmlFromURL(URL):
r = requests.get(TestUrl)
#print r.content
soup = BeautifulSoup(r.content, "html.parser")
#print soup.prettify()
# for link in soup.find_all("table",{"class":"infobox vcard plainlist"}):
# 	print link

for link in soup.find_all("table",{"class":"infobox vcard plainlist"}):
 	# print link.get("class")
 	for lin in link.find_all('tr'):
 		print lin
 		print '_________________________'
 		th = ''
 		td = ''
 		for key in lin.find_all('th'):
 			th = key.text.encode('utf-8')
 		
 		for value in lin.find_all('td'):
 			td = value.text.encode('utf-8')
 		
 		print th," : ", td
 		print '###############'

#print len(soup.find_all("table"))