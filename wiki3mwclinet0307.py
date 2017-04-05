#!/usr/bin/python
#coding:utf-8

import sys
import re
reload(sys)
sys.setdefaultencoding('utf-8')

import wikipedia
#instruction: https://wikipedia.readthedocs.io/en/latest/
import wptools
# instruction: https://github.com/siznax/wptools
import mwclient
#https://github.com/mwclient/mwclient
import mwparserfromhell
import microsofttranslator
import translate
import csv
import codecs, cStringIO
import os.path
from shutil import copyfile
from datetime import datetime
from time import gmtime, strftime
import enchant
import sqlite3

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)




def logMwclient(category,lg = 'zh'):
	s=lg+'.wikipedia.org'
	site = mwclient.Site(('https',s))
	category=site.Categories[category]
	return category

def allpagesin(category):
	result = list()
	for page in category:
		if page.namespace == 14:  # 14 is the category namespace
			result += allpagesin(page)
		else:
			result.append(page.name)
	return result


#Mainly use this function to get all page pageList = GetAllPage('巴哈马人')
def GetAllPage(category):
	categories=logMwclient(category)
	pagelist = allpagesin(categories)
	pagelist = list(set(pagelist))
	return pagelist

def getInfobox(PageName,lg = 'zh'):
	#Real Infobox from wptools,infobox is a dic
	seed = wptools.page(PageName,lang =lg)
	fib=seed.get_parse()
	infobox = fib.infobox
	return infobox

def getWikidata(PageName,lg = 'zh'):
	#wptoolwiki reranged data.wikid is a dic
	seed = wptools.page(PageName,lang =lg)
	getwiki = seed.get_wikidata()
	wikid = getwiki.wikidata
	return wikid

def getWikiPackContent(PageName,lg = 'zh'):
	wikipedia.set_lang(lg)
	pageForName = wikipedia.page(PageName)
	text = pageForName.content
	textPage = re.split('\n=(.+?)\=\n',text)
	ContentDic ={}
	ContentDic['summary']=textPage[0]
	k = 1
	while k <= len(textPage)-2:
		if k %2 !=0 and textPage[k+1].strip(u'\n= ') != '':
			newContent = textPage[k+1].strip(u'\n= ')
			ContentDic[textPage[k].strip(u'\n= ')]=newContent
		k+=1
	return ContentDic,text

def StoreInfobox(infoboxdata,datasource, PageName):
	EachBox = {}
	for item in datasource:
		if item not in EachBox.keys():
			if isinstance(datasource[item],basestring):
				if datasource[item].strip(u'\n') != '':
					EachBox[item] = datasource[item].strip(u'\n')
			else:
				EachBox[item] = ', '.join(datasource[item])

	if PageName not in infoboxdata.keys():
		infoboxdata[PageName]=EachBox
	else:
		for item in EachBox:
			if item not in infoboxdata[PageName].keys():
				infoboxdata[PageName][item] = EachBox[item]

	return infoboxdata

def WriteMiddleInfobox(infoboxdata,PageName):
	#it return dictioanry in which key is str and value is unicode
	try:
		realInfobox = getInfobox(PageName)
		infoboxdata = StoreInfobox(infoboxdata,realInfobox,PageName)
	except:
		print PageName + " no Infobox"
	try:
		realWikidata = getWikidata(PageName)
		infoboxdata = StoreInfobox(infoboxdata,realWikidata,PageName)
	except:
		print PageName + " no Wikidata"
	return infoboxdata


def WriteMiddlePageContent(infoboxdata,PageName):
	#it return dictioanry in which key is str and value is unicode
	try:
		realWikiPackContent = getWikiPackContent(PageName)
		infoboxdata = StoreInfobox(infoboxdata,realWikiPackContent,PageName)
	except:
		print PageName + " no WikiPack"
	return infoboxdata


#delete
def InfoboxDateCheck(text):
	wikicode = mwparserfromhell.parse(text)
	templates = wikicode.filter_templates()
	item1 = templates[0] #Update
	if 'date' in item1.name:
		datelist = item1.params
		date = str(datelist[0])+"/"+str(datelist[1])+"/"+str(datelist[2])
		return date
	else:
		return None
#delete
def InfoboxDetectParse(text):
	wikicode = mwparserfromhell.parse(text)
	templates = wikicode.filter_templates()
	if len(templates) > 0:
		return True
	else:
		return False
#delete
def InfoboxDetectLink(text):
	textcheck = re.compile(ur'\[(.+?)\]', text)
	result= textcheck.findall(text)
	print result
###########################################

def InfoboxBracketCheck(text):
	#[[A|B]] B is real text and A is tooltip
	splitCheck = re.findall(ur'\[(.*?)\]',text)
	sresult = re.split(ur'\[(.*?)\]',text)
	newText = ''
	if len(sresult) != 0:
		for i in sresult:
			if i in splitCheck:
				realSubtext= i.split(u'|')[-1]
				newText = newText + realSubtext.strip(u'[').strip(u']')
			else:
				newText = newText + i.strip(u'[').strip(u']')
	else:
		newText = text
	return newText

def InfoboxNewLinCheck(text):
	#Transfer A<br /> B into A, B
	result = re.findall(ur'\<(.*?)\>',text)
	if len(result) != 0:
		newLineList = []
		for i in result:
			newLineItem = u'<'+i+u'>'
			newLineList.append(newLineItem)

		for item in newLineList:
			text = text.replace(item, ',')
	return text

def InfoboxCheckAll(text):
	text1 = InfoboxBracketCheck(text)
	text2 = InfoboxNewLinCheck(text1)
	return text2

def InfoboxBracketCombine(text):
	#[[A|B]] B is real text and A is tooltip
	splitCheck = re.findall(ur'\[(.*?)\]',text)
	sresult = re.split(ur'\[(.*?)\]',text)
	newText = ''
	if len(sresult) != 0:
		for i in sresult:
			if i in splitCheck:
				realSubtext= i.split(u'|')[-1]
				newText = newText + realSubtext.strip(u'[').strip(u']')
			else:
				newText = newText + i.strip(u'[').strip(u']')
	else:
		newText = text

	#ttype= type(newText)
	result = re.findall(ur'\<(.*?)\>',newText)
	#print result
	if len(result) != 0:
		newLineList = []
		for i in result:
			newLineItem = u'<'+i+u'>'
			newLineList.append(newLineItem)

		for item in newLineList:
			newText = newText.replace(item, u", ")

	return newText

def isfloat(value):
	try:
		float(value)
		return True
	except ValueError:
		return False

def indices(dlist, check):
	indices = [i for i, x in enumerate(dlist) if x == check]
	return indices

def InfoxboxDate(text):
	splitCheck = re.findall(ur'\{{(.*?)\}}',text)
	sresult = re.split(ur'\{{(.*?)\}}',text)
	if len(sresult) != 0:
		#newLineList is to remove blank element form {{}},and collect [{{}},{{}},{{}}]
		newLineList = []
		for i in sresult:
			if i in splitCheck:
				newLineItem = u'{{'+i+u'}}'
				newLineList.append(newLineItem)
			elif i != '':
				newLineItem = i
				newLineList.append(newLineItem)
		result=u''
		for LL in newLineList:
			code = mwparserfromhell.parse(LL)
			templates = code.filter_templates(recursive=True)
			if len(templates)>0:
				template=templates[0]
				dlist= template.params
				if len(dlist) ==0:
					output = str(template.name)
				elif template.name =='coord' and len(dlist)>=2:
					output = str(dlist[0])+','+str(dlist[1])
				elif ('date' in template.name.lower() or  'date' in template.name.lower()) and len(dlist)> 0:
					output = ''
					for i in dlist:
						if i.isdigit():
							startFromDate=-100
							if len(i) == 4 and output =='':
								output += str(i)
								startFromDate = dlist.index(i)
							elif len(i) == 4 and output !='':
								output += ' - '+str(i)
								startFromDate = dlist.index(i)
							else:
								output += '/'+str(i)
				#check something like weight and height which are number {{height and height|m|=|1.78|}}
				elif '=' in dlist:
					SymbolList = indices(dlist,'=')
					output=''
					for i in SymbolList:
						if i>0 and (isfloat(str(dlist[i-1])) or isfloat(str(dlist[i+1]))):
							subOutput = ''
							if isfloat(str(dlist[i+1])):
								subOutput += str(dlist[i+1]) + ' '+str(dlist[i-1])
							elif isfloat(str(dlist[i-1])) :
								subOutput += str(dlist[i-1]) + ' '+str(dlist[i+1])
							if output != '':
								output += ', '+subOutput
							else:
								output += subOutput
				else:
					if len(dlist) >0:
						output = ','.join(str(x) for x in dlist)
				if result == '' and output != '':
					result+=output
				elif output != '':
					result += '; '+output
			else:
				if result == '' and LL != '':
					result+=LL
				elif LL != '':
					result += '; '+LL
	return result

def ParseInfoboxBracketAndTemplate(text):
	removeBracket = InfoboxCheckAll(text)
	removeTemplate = InfoxboxDate(removeBracket)
	return removeTemplate

def InfoboxPrint(text):
	exam2=ParseInfoboxBracketAndTemplate(text)
	print repr(exam2)[0:0], exam2

def TranslatorMicrosoftLogin():
	return microsofttranslator.Translator('xuzhuo8837863', 'BtdC5PupdH+d9wHqRJPr4fW6twYCppM0qeJLEd3xg4s=')

def TranslatorDect(text, translator):
	return translator.detect_language(text)

def TranslatorResultFromMS(text, translator):
	return translator.translate(text, "zh")

def TranslatorResultFromMM(text):
	translator= translate.Translator(to_lang="zh")
	if text[-1].isdigit():
		num = text[-1]
		toTranslate = text[:-1].strip()
		translation = translator.translate(toTranslate)+num
	else:
		translation = translator.translate(text)
	if 'MYMEMORY WARNING' in translation:
		translation=''
	return translation

def CheckKeyNumIn(text):
	if text[-1].isdigit():
		textResult = text[:-1]
		endNum = text[-1]
	else:
		textResult=text
		endNum=''
	return textResult.strip(),endNum

def keyModify(text):
	textPage = re.split(r"([a-z]+)([0-9]+)",text)
	if len(textPage) >0:
		text2 = " ".join(textPage)
	else:
		text2 = text
	textlist = text2.split('_')
	textstring=" ".join(x.strip() for x in textlist)
	return textstring

def wikiKeyTranslateCSVWrite(keyen,keyzh,pagename,filename):
	pass

def wikiKeyTranslateCSVRead(filename='wikiKeyTranslation.csv'):
	translateDataFromCSV={}
	if os.path.isfile(filename) and os.path.getsize(filename) > 0:
		filenamebackup=filename[:-4]+'Backup'+str(datetime.now()).split(' ')[0]+'.csv'
		copyfile(filename,filenamebackup)
		with open(filename) as csvfileR:
			readCSV = csv.reader(csvfileR, delimiter=',')
			#next(readCSV)
			for row in readCSV:
				try:
					translateDataFromCSV[row[0]]=row[1]
				except:
					pass
			csvfileR.close()
	return translateDataFromCSV

def is_ascii(s):
    return all(ord(c) < 128 for c in s)




########## Python Code about SQLite ############
def PersonNameCreateTable(c):
	c.execute('''CREATE TABLE IF NOT EXISTS PersonName
		(PersonNameId INTEGER PRIMARY KEY, name TEXT, Category TEXT, IsFinished INTEGER)''')
	print 'PersonName table has been created'

def PersonNameAddRecords(c,name, categoryName, IsFinished = 0):
	c.execute('''INSERT INTO PersonName (name, Category, IsFinished)
	VALUES (?,?,?)''',(name, categoryName, IsFinished))

def PersonPropertyCreateTable(c):
	c.execute('''CREATE TABLE IF NOT EXISTS PersonProperty
		(PersonPropertyId INTEGER PRIMARY KEY, PropertyNameZH TEXT, adjPropertyNameOriginal TEXT, 
		PropertyNameOriginal TEXT, IsTranslated INTEGER)''')
	print 'PersonProperty table has been created'


def PersonPropertyAddRecords(c,PropertyNameZH, adjPropertyNameOriginal, PropertyNameOriginal,IsTranslated ):
	c.execute('''INSERT INTO PersonProperty (PropertyNameZH, adjPropertyNameOriginal, 
	PropertyNameOriginal, IsTranslated )
	VALUES (?,?,?,?)''',(PropertyNameZH, adjPropertyNameOriginal, PropertyNameOriginal,IsTranslated))

def InfoboxCreateTable(c):
	c.execute('''CREATE TABLE IF NOT EXISTS Infobox
		(InfoboxId INTEGER PRIMARY KEY, PersonNameId INTEGER, PersonPropertyId INTEGER, 
		InfoboxContentParse TEXT, InfoboxTemplate TEXT)''')
	print 'Infobox table has been created'

def InfoboxAddRecords(c,PersonNameId, PersonPropertyId, InfoboxContentParse, InfoboxTemplate):
	c.execute('''INSERT INTO Infobox (PersonNameId, PersonPropertyId , 
	InfoboxContentParse, InfoboxTemplate)
	VALUES (?,?,?,?)''',(PersonNameId, PersonPropertyId, InfoboxContentParse, InfoboxTemplate))	

def PageContentWholeCreateTable(c):
	c.execute('''CREATE TABLE IF NOT EXISTS PageContentWhole
		(PageContentWholeId INTEGER PRIMARY KEY, PersonNameId INTEGER, 
		PageContent TEXT)''')
	print 'PageContentWhole table has been created'

def PageContentWholeAddRecords(c,PersonNameId, PageContent):
	c.execute('''INSERT INTO PageContentWhole (PersonNameId, PageContent)
	VALUES (?,?)''',(PersonNameId, PageContent))

def PageContentSectionPropertyCreateTable(c):
	c.execute('''CREATE TABLE IF NOT EXISTS PageContentSectionProperty
		(PageContentSectionId INTEGER PRIMARY KEY, PageContentSectionName TEXT)''')
	print 'PageContentSectionProperty table has been created'

def PageContentSectionPropertyAddRecords(c,PageContentSectionName):
	date = strftime("%Y-%m-%d %H:%M:%S", gmtime())
	c.execute('''INSERT INTO PageContentSectionProperty
	(PageContentSectionName)
	VALUES (?)''',(PageContentSectionName,))

def PageContentSplitCreateTable(c):
	c.execute('''CREATE TABLE IF NOT EXISTS PageContentSplit
	(PageContentSplitId INTEGER PRIMARY KEY, PersonNameId INTEGER, 
	PageContentSectionId INTEGER, PageContent TEXT)''')
	print 'PageContentSplit table has been created'

def PageContentSplitAddRecords(c,PersonNameId, PageContentSectionId, PageContent):
	c.execute('''INSERT INTO PageContentSplit (PersonNameId, PageContentSectionId, PageContent)
	VALUES (?,?,?)''',(PersonNameId, PageContentSectionId,PageContent))

def TranslationCreateTable(c):
	c.execute('''CREATE TABLE IF NOT EXISTS Translation
		(TranslationId INTEGER PRIMARY KEY, TermEN TEXT, TermZH TEXT, PageName TEXT)''')
	print 'Translation table has been created'

def TranslationAddRecords(c,TermEN,TermZH, PageName):
	c.execute('''INSERT INTO Translation (TermEN,TermZH, PageName)
	VALUES (?,?,?)''',(TermEN,TermZH, PageName))


def DropTable(c,TableName):
	dropTableString='DROP TABLE IF EXISTS '+TableName
	c.execute(dropTableString)
	print 'Table Dropped'

def FinishAndEndSQL(c,conn):
	conn.commit()
	c.close()
	conn.close()
	print '### SQL script executed ###'

def ErrorPageNameCreateTable(c):
	c.execute('''CREATE TABLE IF NOT EXISTS ErrorPageName
	(ErrorPageNameId INTEGER PRIMARY KEY, PersonNameId INTEGER, 
	name TEXT, Category TEXT, IsSolved INTEGER)''')
	print 'ErrorPageName table has been created'

def ErrorPageNameAddRecords(c,PersonNameId, name, Category):
	IsSolved = 0
	c.execute('''INSERT INTO ErrorPageName (PersonNameId, name, Category, IsSolved)
	VALUES (?,?,?,?)''',(PersonNameId, name, Category, IsSolved))

def ErrorPropertyCreateTable(c):
	c.execute('''CREATE TABLE IF NOT EXISTS ErrorProperty
	(ErrorPropertyId INTEGER PRIMARY KEY, PersonNameId INTEGER, 
	name TEXT, SourceColumnName TEXT, IsSolved INTEGER, Source TEXT, ErrorInfo TEXT)''')
	print 'ErrorProperty table has been created'

def ErrorPropertyAddRecords(c,PersonNameId, name, SourceColumnName,source,ErrorInfo):
	IsSolved = 0
	c.execute('''INSERT INTO ErrorProperty (PersonNameId, name, SourceColumnName, IsSolved, Source, ErrorInfo)
	VALUES (?,?,?,?,?,?)''',(PersonNameId, name, SourceColumnName, IsSolved, source, ErrorInfo))

def CreateAllTable(c):
	#ErrorPropertyCreateTable(c)
	ErrorPageNameCreateTable(c)
	PersonNameCreateTable(c)
	PersonPropertyCreateTable(c)
	InfoboxCreateTable(c)
	PageContentWholeCreateTable(c)
	PageContentSectionPropertyCreateTable(c)
	PageContentSplitCreateTable(c)
	TranslationCreateTable(c)

def DropAllTable(c):
	DropTable(c,'ErrorProperty')
	DropTable(c,'ErrorPageName')
	DropTable(c,'PersonName')
	DropTable(c,'PersonProperty')
	DropTable(c,'Infobox')
	DropTable(c,'PageContentWhole')
	DropTable(c,'PageContentSectionProperty')
	DropTable(c,'PageContentSplit')
	DropTable(c,'Translation')


def ReadFromDb(c, column, Table, WHERE ='',duplicate='n'):
	# WHERE should include word 'where'
	#if column is ONE string: return a list of value for that column
	#if column is a list, please put the key on the list item of list column, 
	#it will return a dictionary which key is the first item of list, values are tuple of the rest item of list
	#like {column[0]:(column[1],column[2],...),column[0]:(column[1],column[2],...),column[0]:(column[1],column[2],...)}
	if type(column) is not list:
		sqlscript = 'SELECT '+column+' FROM '+Table +' '+WHERE
		print sqlscript
		c.execute(sqlscript)
		data = c.fetchall()
		return [i[0] for i in data]
		#return: the type for item in list is what it insert
	else:
		columnList = ', '.join(column)
		sqlscript = 'SELECT '+columnList+' FROM '+Table +' '+WHERE
		print sqlscript
		c.execute(sqlscript)
		data = c.fetchall()
		if duplicate == 'n':
			return {str(i[0]): i[1:] for i in data} #return dictionary #return a list in which the key is a string and value is list in which it item is what it insert
		else:
			return data # data is a tuple
		

def UpdateTable(c,Table,UpdateColumn, UpdateValue,ConditionalColumn, ConditionalValue):
	if isinstance(UpdateValue,int):
		UpdateEqual = ' = '
		UpdateWhere = ' WHERE '
		UpdateValue = str(UpdateValue)
	else:
		UpdateEqual = ' = "'
		UpdateWhere = '" WHERE '
	if isinstance(ConditionalValue,int):
		ConditionalEqual = ' = '
		ConditionalEnd = ''
		ConditionalValue = str(ConditionalValue)
	else:
		ConditionalEqual = ' = "'
		ConditionalEnd = '"'
	sqlscript='UPDATE ' + Table+' SET '+UpdateColumn+UpdateEqual+UpdateValue + UpdateWhere+ ConditionalColumn + ConditionalEqual+ConditionalValue+ConditionalEnd
	print sqlscript
	c.execute(sqlscript)
	print 'Table has been updated'


def UpdateTableMultiple(c,Table,UpdateDic,ConditionalColumn, ConditionalValue):
	#UpdateDic = {columnName: columnValue, columnName:columnValue}
	sqlUpdatePart = ', '.join([((i +' = '+ str(UpdateDic[i])) if isinstance(UpdateDic[i],int) else (i +' = "'+ UpdateDic[i]+'"')) for i in UpdateDic])
	if isinstance(ConditionalValue,int):
		ConditionalEqual = ' = '
		ConditionalEnd = ''
		ConditionalValue = str(ConditionalValue)
	else:
		ConditionalEqual = ' = "'
		ConditionalEnd = '"'
	sqlscript='UPDATE ' + Table+' SET '+sqlUpdatePart + " Where "+ ConditionalColumn + ConditionalEqual+ConditionalValue+ConditionalEnd
	print sqlscript
	c.execute(sqlscript)
	print 'Table has been updated'

def DeleteTable(c,Table,column='', OriginalValue =''):
	if OriginalValue =='' and column =='':
		sqlscript='DELETE FROM ' + Table
	elif isinstance(OriginalValue,int):
		OriginalValue = str(OriginalValue)
		sqlscript='DELETE FROM ' + Table+ ' WHERE '+ column + ' = '+OriginalValue
	else:
		sqlscript='DELETE FROM ' + Table+ ' WHERE '+ column + ' = "'+OriginalValue+'"'
	c.execute(sqlscript)
	print 'Values in table has been deleted'


def UpdatePropertyNameZH(c,conn):
	wholePersonPorperty = ReadFromDb(c, ["adjPropertyNameOriginal","PersonPropertyId","PropertyNameZH","PropertyNameOriginal"], "PersonProperty", 'WHERE IsTranslated = 1','y')
	#wholePersonPorperty = tuple("adjPropertyNameOriginal","PersonPropertyId","PropertyNameZH")
	TranslationTable = ReadFromDb(c, ["TermEN","TermZH"],"Translation")
	#TranslationTable is a dictionary = {TermEN: TermZH}
	updateDic={}
	for i in wholePersonPorperty:
		if CheckKeyNumIn(i[2])[0] !=  TranslationTable[i[0]][0]:
			print CheckKeyNumIn(i[2])[0]
			print TranslationTable[i[0]][0]
			updateDic[i[1]] = TranslationTable[i[0]][0]+CheckKeyNumIn(i[3])[1]
	for k in updateDic:
		UpdateTable(c,"PersonProperty",'PropertyNameZH', updateDic[k],"PersonPropertyId", k)
	conn.commit()


def LoadPersonNameFromWiki(categoryName):
	wikipage = GetAllPage(categoryName)
	existNameList=ReadFromDb(c,'name','PersonName')
	n=0
	for i in wikipage:
		if i not in existNameList:
			n+=1
			PersonNameAddRecords(c,i,categoryName)
		else:
			print i +' exists in PersonName Table '
	print str(n) + ' people have be loaded into PersonName Table'


def CountInSQL(c,table,column,value, OtherColumn = ''):
	#OtherColumn should start with comma like ', column1, column2'
	sqlscript='SELECT COUNT(*) '+OtherColumn+' FROM '+table+' WHERE ' + column + " = '"+str(value)+"'"
	c.execute(sqlscript)
	data = c.fetchall()
	if OtherColumn =='':
		return data[0][0]
	else:
		return data[0]

def ProcessEachPage(c,PageName,Category=''):
	infoboxdata={}
	#str=unicode!=buffer
	k=WriteMiddleInfobox(infoboxdata,PageName)
	
	#it return dictioanry in which key is str and value is unicode
	translateData =  ReadFromDb(c, ['TermEN','TermZH'], 'Translation') #### When loop for each name, think it deeply
	#return a list in which the key is a string and value is list in which it item is what it insert
	PropertyNameOriginalList= ReadFromDb(c,'PropertyNameOriginal','PersonProperty')
	
	#chekc and Write PersonName
	(countPersonName, PersonNameId) = CountInSQL(c,"PersonName","Name",PageName,', PersonNameId')
	if countPersonName >0:
		#date = strftime("%Y-%m-%d %H:%M:%S", gmtime())
		UpdateDic={"IsFinished": 1,"Category":Category}
		UpdateTableMultiple(c,"PersonName",UpdateDic,"name", PageName)
	else:
		PersonNameAddRecords(c,unicode(PageName,"utf-8"), Category,1)
		PersonNameId =c.lastrowid

	ErrorCount = 0
	print k 
	for m in k:
		print m
		print k[m] 
	for i in k[PageName]:
		try:
			key = keyModify(i).strip()
			key1= key.split(' ')[0]#get 'birth' from 'birth_day'
			lgDt=is_ascii(key1)
			if lgDt:
				keyWriteInCSV = CheckKeyNumIn(key.strip())[0]
				print keyWriteInCSV
				if keyWriteInCSV in translateData.keys():
					keyTranslated = translateData[keyWriteInCSV][0]
				else:
					keyTranslated = TranslatorResultFromMM(keyWriteInCSV)
					translateData[keyWriteInCSV]=(keyTranslated,)
					#keyWriteInCSV, keyTranslated and PageName are all unicode
					TranslationAddRecords(c,unicode(keyWriteInCSV,"utf-8"),keyTranslated, unicode(PageName,"utf-8"))
				print i," : ",lgDt," : ", keyTranslated+CheckKeyNumIn(key)[1]," : ", ParseInfoboxBracketAndTemplate(k[PageName][i]),', ','Template: ',k[PageName][i]	
				PropertyNameZH = keyTranslated+unicode(CheckKeyNumIn(key)[1],"utf-8") #unicode
				adjPropertyNameOriginal = keyWriteInCSV #str
			else:
				print i," : ",lgDt," : ", i," : ", ParseInfoboxBracketAndTemplate(k[PageName][i]),', ','Template: ',k[PageName][i]
				PropertyNameZH = i #str
				adjPropertyNameOriginal = i #str
			PropertyNameOriginal=i #str
			IsTranslated = lgDt
			
			#Check and Write PersonProperty
			(countPropertyNameOriginal, PersonPropertyId) = CountInSQL(c,"PersonProperty","PropertyNameOriginal",PropertyNameOriginal,', PersonPropertyId')
			if countPropertyNameOriginal == 0: #Write into PersonProperty
				PersonPropertyAddRecords(c,PropertyNameZH, adjPropertyNameOriginal, PropertyNameOriginal,IsTranslated )
				PersonPropertyId = c.lastrowid
			print "PersonPropertyId :", PersonPropertyId

			#Check and Write Infobox
			IFBsqlscript='SELECT COUNT(*) FROM Infobox WHERE PersonNameId = '+str(PersonNameId)+' AND PersonPropertyId = '+ str(PersonPropertyId)
			c.execute(IFBsqlscript)
			IFBdata = c.fetchall()[0]
			countInfbox = IFBdata[0]
			InfoboxContentParse = ParseInfoboxBracketAndTemplate(k[PageName][i])
			InfoboxTemplate = k[PageName][i]
			if countInfbox == 0:
				InfoboxAddRecords(c,PersonNameId, PersonPropertyId, InfoboxContentParse, InfoboxTemplate)
		except Exception as e:
			print e.message
			ErrorCount+=1
			ErrorPropertyAddRecords(c,PersonNameId, unicode(PageName,"utf-8"), i, 'PersonProperty: PropertyNameOriginal', e.message)
	try:
		# Page Content
		p, ptext=getWikiPackContent(PageName)  #return dic and unicode
		#Check and Write PageContentWhole
		countPageContentWhole = CountInSQL(c,"PageContentWhole","PersonNameId",PersonNameId)
		if countPageContentWhole == 0:
			PageContentWholeAddRecords(c,PersonNameId, ptext)

		#PageContentPart
		for h in p:
			#Check and Write PageContentSectionProperty
			(countPageContentSectionProperty, PageContentSectionId) = CountInSQL(c,"PageContentSectionProperty","PageContentSectionName",h,', PageContentSectionId')
			if countPageContentSectionProperty == 0:
				PageContentSectionPropertyAddRecords(c,h)
				PageContentSectionId = c.lastrowid

			#Check and Write PageContentSplit
			PCSsqlscript='SELECT COUNT(*) FROM PageContentSplit WHERE PersonNameId = '+str(PersonNameId)+' AND PageContentSectionId = '+ str(PageContentSectionId)
			c.execute(PCSsqlscript)
			PCSdata = c.fetchall()[0]
			countPageContentSplit = PCSdata[0]
			PageContent = p[h]
			if countPageContentSplit == 0:
				PageContentSplitAddRecords(c,PersonNameId, PageContentSectionId, PageContent)
	except Exception as e:
		print e.message
		ErrorCount +=1
		ErrorPropertyAddRecords(c,PersonNameId, unicode(PageName,"utf-8"), 'PageContent', 'PageContentWhole/Split',e.message)
	return PersonNameId, ErrorCount

def AddDataWhole(LimitNumber = '',condition = ''):
	if LimitNumber != '':
		condition = 'where IsFinished = 0 '+condition+'limit '+str(LimitNumber)
	else:
		condition = 'where IsFinished = 0 '+condition
	NameAndCategoryList = ReadFromDb(c, ['name','Category'], 'PersonName', condition)
	if len(NameAndCategoryList) !=0:
		n=1
		ErrorCount = 0
		for name in NameAndCategoryList:
			print '#'*30
			print name+'   '+ str(n)+' / ' +str(len(NameAndCategoryList))
			print '#'*30
			PersonNameId, ErrorCountAdd = ProcessEachPage(c,name, NameAndCategoryList[name][0])
			if n == 1:
				PersonNameIdMin = PersonNameId
			n+=1
			print '^'*50
			
		print "PersonNameId starts from : " +str(PersonNameIdMin)
		if ErrorCount !=0:
			print str(ErrorCount) + " records has been added into ErrorProperty table"
	else:
		print 'No record can be added into database'

conn = sqlite3.connect('wiki.db')
c = conn.cursor()

#https://zh.wikipedia.org/wiki/Category:%E5%90%84%E5%9C%8B%E4%BA%BA%E7%89%A9

#ProcessEachPage(c,'范冰冰')
# realInfobox = getInfobox('范冰冰')
# realWikidata = getWikidata('范冰冰')
# print realInfobox
# print realWikidata
# #realWikiPackContent = getWikiPackContent('杨幂')
# #print [i for i in realWikiPackContent]

# infoboxdata={}
# k = WriteMiddleInfobox(infoboxdata,'范冰冰')
# infoboxdata = StoreInfobox(infoboxdata,realWikidata,'范冰冰')
# print "#"*15
# for i in infoboxdata:
# 	print i
# 	for j in infoboxdata[i]: 
# 		print j, infoboxdata[i][j]



#PersonNameAddRecords(c,u'范冰冰', '', IsFinished = 0)




	
#categoryName=u'卢森堡人'
#LoadPersonNameFromWiki(categoryName)
AddDataWhole('',' and name = "范冰冰"')
#UpdatePropertyNameZH(c,conn)




FinishAndEndSQL(c,conn)
