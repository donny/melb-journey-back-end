from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.api import mail
from django.utils import simplejson

import cgi
import re
import ClientForm
import logging
import sys
import traceback

class MainPage(webapp.RequestHandler):
	def get(self):
		self.response.headers['Content-Type'] = 'text/plain'
		self.response.out.write('Worqbench')



# Sample test queries:
# curl 'http://localhost:8080/listJourneys' --data 'dateTime=6#200902#7#50#pm&nameOrigin=caulfield+railway+station+%28caulfield+east%29&nameDestination=flinders+street+railway+station+%28melbourne+city%29'

class ListJourneys(webapp.RequestHandler):
	def post(self):
		self.response.headers['Content-Type'] = 'text/plain'
		finalResults = []
		memKey = ''

		# Get the parameters
		dateTime = cgi.escape(self.request.get('dateTime'))
		nameOrigin = cgi.escape(self.request.get('nameOrigin'))
		nameDestination = cgi.escape(self.request.get('nameDestination'))
		#logging.info("LJ: " + dateTime + " " + nameOrigin + " " + nameDestination + ".")
		if dateTime == "" or nameOrigin == "" or nameDestination == "":
			returnError(self, "Invalid queries.")
			return

		memKey = dateTime + nameOrigin + nameDestination
		memVal = memcache.get(memKey)
		if memVal is not None:
			self.response.out.write(memVal)
			return

		dateTime = dateTime.split('#')
		dateDay = dateTime[0]
		dateYearMonth = dateTime[1]
		timeHour = dateTime[2]
		timeMinute = dateTime[3]
		timeAMPM = dateTime[4]

		if timeAMPM == '':
			timeHourInt = int(timeHour)
			if timeHourInt == 0:
				timeHour = '12'
				timeAMPM = 'am'	
			elif 0 < timeHourInt and timeHourInt < 12:
				timeHour = str(timeHourInt)
				timeAMPM = 'am'	
			elif timeHourInt == 12:
				timeHour = '12'
				timeAMPM = 'pm'	
			else:
				timeHour = str(timeHourInt - 12)
				timeAMPM = 'pm'

		timeMinuteInt = int(timeMinute)
		timeMinuteInt = (timeMinuteInt - (timeMinuteInt % 5))
		timeMinute = str(timeMinuteInt)

		timeAMPM = timeAMPM.lower()
		if timeAMPM.startswith('a'):
			timeAMPM = 'am'
		else:
			timeAMPM = 'pm'

		# Get the HTML data
		homePageContent = ''
		homeAddress = "http://www.metlinkmelbourne.com.au/"
		try:
			homePage = urlfetch.fetch(homeAddress)
			if homePage.status_code != 200:
				raise Exception("")
			homePageContent = homePage.content
		except:
			returnError(self, "Service unavailable.", "WARNING")
			return

		try:
			homePageForms = ClientForm.ParseFile(homePageContent, homeAddress, backwards_compat=False)
			form = homePageForms[0]
			form["itdDateDay"] = [dateDay]
			form["itdDateYearMonth"] = [dateYearMonth]
			form["itdTimeHour"] = [timeHour]
			form["itdTimeMinute"] = [timeMinute]
			form["itdTimeAMPM"] = [timeAMPM]
			form["name_origin"] = nameOrigin
			form["name_destination"] = nameDestination
			formSubmit = form.click()
			formSubmitAddress = formSubmit.get_full_url()
			formSubmitPage = urlfetch.fetch(formSubmitAddress)
			rawData = formSubmitPage.content

			fileEncoding = "iso-8859-1"
			dataString = rawData.decode(fileEncoding)
			dataString = dataString.encode("ascii", "ignore")
		except:
			returnError(self, "Service unavailable.", "ERROR")
			return

		## START OF DATA PROCESSING
		try:
			data0 = re.findall('<tr class="p.">(.*?)</tr>', dataString, re.DOTALL)
			resultSessionID = re.findall('&amp;sessionID=(.*?)&amp', dataString, re.DOTALL)

			for data1 in data0:
				data2 = re.findall('<td(.*?)</td>', data1, re.DOTALL)
				resultOption = re.findall('<div align="center">(.*?)</div>', data2[0], re.DOTALL)
				resultDepart = re.findall('<span>(.*?)</span>', data2[1], re.DOTALL)
				if len(resultDepart) == 0:
					resultDepart.insert(0, '')
				resultArrive = re.findall('<span>(.*?)</span>', data2[2], re.DOTALL)
				if len(resultArrive) == 0:
					resultArrive.insert(0, '')
				resultDuration = re.findall('<div align="center">(.*?)</div>', data2[3], re.DOTALL)
				finalResults.append({'journeyOption': resultOption[0], 'journeyDepart': resultDepart[0], 'journeyArrive': resultArrive[0], 'journeyDuration': resultDuration[0], 'journeySessionID': resultSessionID[0]})

		except:
			returnError(self, "Processing error.", "ERROR")
			return
		## DATA OUTPUT
		finalResults.insert(0, {'status': "WORQ-OK", 'message': "LJ-OK"})
		memVal = simplejson.dumps(finalResults)
		memcache.set(key = memKey, value = memVal, time = 300)
		self.response.out.write(memVal)
		## END OF DATA PROCESSING



# Sample test queries:
# curl 'http://localhost:8080/searchLocations' --data 'query=caulfield'
# curl 'http://localhost:8080/searchLocations' --data 'query=caulfield north'

class SearchLocations(webapp.RequestHandler):
	def post(self):
		self.response.headers['Content-Type'] = 'text/plain'
		finalResults = []
		memKey = ''

		# Get the parameters
		query = cgi.escape(self.request.get('query'))
		#logging.info("SL: " + query + ".")
		if query == "":
			returnError(self, "Invalid queries.")	
			return

		memKey = query
		memVal = memcache.get(memKey)
		if memVal is not None:
			self.response.out.write(memVal)
			return

		# Get the HTML data
		homePageContent = ''
		homeAddress = "http://www.metlinkmelbourne.com.au/"
		try:
			homePage = urlfetch.fetch(homeAddress)
			if homePage.status_code != 200:
				raise Exception("")
			homePageContent = homePage.content
		except:
			returnError(self, "Service unavailable.", "WARNING")
			return

		try:
			homePageForms = ClientForm.ParseFile(homePageContent, homeAddress, backwards_compat=False)
			form = homePageForms[0]
			form["name_origin"] = query
			formSubmit = form.click()
			formSubmitAddress = formSubmit.get_full_url()
			formSubmitPage = urlfetch.fetch(formSubmitAddress)
			rawData = formSubmitPage.content

			fileEncoding = "iso-8859-1"
			dataString = rawData.decode(fileEncoding)
			dataString = dataString.encode("ascii", "ignore")
		except:
			returnError(self, "Service unavailable.", "ERROR")
			return

		## START OF DATA PROCESSING
		try:
			data0 = re.findall('<select name="name_origin"(.*?)</select>', dataString, re.DOTALL)

			if len(data0) == 0:
				finalResults.insert(0, {'status': "WORQ-OK", 'message': "SL-NOTFOUND"})
				memVal = simplejson.dumps(finalResults)
				memcache.set(key = memKey, value = memVal, time = 300)
				self.response.out.write(memVal)
				return

			data1 = re.findall('<optgroup label="(.*?):">(.*?)</optgroup>', data0[0], re.DOTALL)

			for data2 in data1:
				resultTransportType = data2[0]
				#self.response.out.write(data2[0] + '\n')
				data3 = re.findall('<option.*?>(.*?)</option>', data2[1], re.DOTALL)
				resultTransportLocations = []
				for data4 in data3:
					resultTransportLocations.append(data4)			
					#self.response.out.write('    ' + data4 + '\n')
				finalResults.append({'transportType': resultTransportType, 'transportLocations': resultTransportLocations})

		except:
			returnError(self, "Processing error.", "ERROR")
			return
		## DATA OUTPUT
		finalResults.insert(0, {'status': "WORQ-OK", 'message': "SL-OK"})
		memVal = simplejson.dumps(finalResults)
		memcache.set(key = memKey, value = memVal, time = 300)
		self.response.out.write(memVal)
		## END OF DATA PROCESSING



# Sample test queries:
# curl 'http://localhost:8080/getDetails' --data 'session=VICWA04_2286479531&selection=4'

class GetDetails(webapp.RequestHandler):
	def post(self):
		self.response.headers['Content-Type'] = 'text/plain'
		finalResults = []
		memKey = ''

		# Get the parameters
		session = cgi.escape(self.request.get('session'))
		selection = cgi.escape(self.request.get('selection'))
		#logging.info("GD: " + session + " " + selection + ".")
		if session == "" or selection == "":
			returnError(self, "Invalid queries.")
			return

		memKey = session + selection
		memVal = memcache.get(memKey)
		if memVal is not None:
			self.response.out.write(memVal)
			return

		# Get the HTML data
		homePageContent = ''
		homeAddress = "http://jp.metlinkmelbourne.com.au/metlink/XSLT_TRIP_REQUEST2?language=en&sessionID=" + session + "&requestID=1&command=nop&tripSelection=on&tripSelector" + selection + "=1&itdLPxx_view=detail&itdLPxx_return=&itdLPxx_emailAddress_origin=&itdLPxx_emailAddress_destination="
		try:
			homePage = urlfetch.fetch(homeAddress)
			if homePage.status_code != 200:
				raise Exception("")
			homePageContent = homePage.content
		except:
			returnError(self, "Service unavailable.", "WARNING")
			return

		try:
			rawData = homePageContent

			fileEncoding = "iso-8859-1"
			dataString = rawData.decode(fileEncoding)
			dataString = dataString.replace(u'\u00a0', ' ')
			dataString = dataString.encode("ascii", "ignore")
		except:
			returnError(self, "Service unavailable.", "ERROR")
			return

		## START OF DATA PROCESSING
		try:
			data0 = re.findall('<tr class="p.*?results">(.*?)</tr>', dataString, re.DOTALL)
			resultDetails = []
			for data1 in data0:
				data2 = re.findall('<td.*?>(.*?)</td>', data1, re.DOTALL)
				resultTravelBy = re.findall('alt="(.*?)">', data2[0], re.DOTALL)
				#resultDepArr = re.findall('(.*?):', data2[1], re.DOTALL)
				resultTravelTime = re.findall('<span>(.*?)</span>', data2[2], re.DOTALL)
				resultTravelStop = re.findall('stop/view/(.*?)"', data2[3], re.DOTALL)
				resultTravelDesc = data2[3]
				resultTravelDesc = re.sub('<br>', ' ', resultTravelDesc)
				resultTravelDesc = re.sub('<.*?>', '', resultTravelDesc)
				resultTravelDesc = re.sub(' +', ' ', resultTravelDesc)

				resultDetailsPrefix = "NONE"

				if len(resultTravelBy):
					resultDetails.append("HEAD#Travel by " + resultTravelBy[0])
				#if len(resultDepArr):
				#	resultDepArr[0] = re.sub('<.*?>', '', resultDepArr[0])
				#	self.response.out.write(resultDepArr[0] + '\n')
				if len(resultTravelTime):
					resultTravelDesc += " (" + resultTravelTime[0] + ")"

				if len(resultTravelStop):
					resultDetailsPrefix = "MAP-" + resultTravelStop[0]

				resultDetails.append(resultDetailsPrefix + "#" + resultTravelDesc)

			finalResults.append({'details': resultDetails})

		except:
			returnError(self, "Processing error.", "ERROR")
			return
		## DATA OUTPUT
		finalResults.insert(0, {'status': "WORQ-OK", 'message': "GD-OK"})
		memVal = simplejson.dumps(finalResults)
		memcache.set(key = memKey, value = memVal, time = 300)
		self.response.out.write(memVal)
		## END OF DATA PROCESSING



# Sample test queries:
# curl 'http://localhost:8080/getStopInfo' --data 'stop=16440'

class GetStopInfo(webapp.RequestHandler):
	def post(self):
		self.response.headers['Content-Type'] = 'text/plain'
		finalResults = []
		memKey = ''

		# Get the parameters
		stop = cgi.escape(self.request.get('stop'))
		#logging.info("GSI: " + stop + ".")
		if stop == "":
			returnError(self, "Invalid queries.")
			return

		memKey = stop
		memVal = memcache.get(memKey)
		if memVal is not None:
			self.response.out.write(memVal)
			return

		# Get the HTML data
		homePageContent = ''
		homeAddress = "http://www.metlinkmelbourne.com.au/stop/view/" + stop
		try:
			homePage = urlfetch.fetch(homeAddress)
			if homePage.status_code != 200:
				raise Exception("")
			homePageContent = homePage.content
		except:
			returnError(self, "Service unavailable.", "WARNING")
			return

		try:
			rawData = homePageContent

			fileEncoding = "iso-8859-1"
			dataString = rawData.decode(fileEncoding)
			dataString = dataString.replace(u'\u00a0', ' ')
			dataString = dataString.encode("ascii", "ignore")
		except:
			returnError(self, "Service unavailable.", "ERROR")
			return

		## START OF DATA PROCESSING
		try:
			data0 = re.findall('<td class="address adr">(.*?)</td>', dataString, re.DOTALL)

			data1 = re.findall('<span.*?>(.*?)</span>', data0[0], re.DOTALL)

			resultStreetAddress = data1[0]
			resultLocality = data1[1]
			resultPostalCode = data1[2]

			resultStreetAddress = re.sub('/', 'and', resultStreetAddress)

			stopAddress = resultStreetAddress + ", " + resultLocality + ", " + resultPostalCode + ", Victoria, Australia"

			finalResults.append({'address': stopAddress})

		except:
			returnError(self, "Processing error.", "ERROR")
			return
		## DATA OUTPUT
		finalResults.insert(0, {'status': "WORQ-OK", 'message': "GSI-OK"})
		memVal = simplejson.dumps(finalResults)
		memcache.set(key = memKey, value = memVal, time = 300)
		self.response.out.write(memVal)
		## END OF DATA PROCESSING



application = webapp.WSGIApplication([('/', MainPage), 
																		('/searchLocations', SearchLocations),
																		('/listJourneys', ListJourneys),
																		('/getDetails', GetDetails),
																		('/getStopInfo', GetStopInfo)
																		], debug=True)

def returnError(handler, message, level="INFO"):
	reqPath = handler.request.path
	reqBody = handler.request.body
	logMesg = message + " (" + reqPath + " " + reqBody + ")"

	if level == "INFO":
		logging.info(logMesg)
	elif level == "WARNING":
		logging.warning(logMesg)
	elif level == "ERROR":
		logMesgDetail = ""
		et, ev, tb = sys.exc_info()
		logMesgDetail += str(et) + " "
		logMesgDetail += str(ev) + " "
		while tb:
			co = tb.tb_frame.f_code
			line_no = "#" + str(traceback.tb_lineno(tb)) + " "
			logMesgDetail += line_no 
			tb = tb.tb_next
		logging.error(logMesg + " " + logMesgDetail)
		mail.send_mail(sender = "info@worqbench.com",
              to = "info+appengine@worqbench.com",
              subject = "Melbourne Journey ERROR",
              body = logMesg + " " + logMesgDetail)

	finalResults = []
	finalResults.append({'status': "WORQ-ERROR", 'message': message})
	handler.response.out.write(simplejson.dumps(finalResults))

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
