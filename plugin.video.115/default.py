# -*- coding: utf-8 -*-
# default.py
import os,json,xbmc,xbmcgui,cookielib,gzip,urllib,urllib2,re,urlparse,time,threading,socket,HTMLParser,uuid
from datetime import timedelta,datetime,time as dtime
from StringIO import StringIO
from xbmcswift2 import Plugin, ListItem

reload(sys)
sys.setdefaultencoding('utf-8')

import comm
plugin = comm.plugin
setthumbnail=comm.setthumbnail
__cwd__=comm.__cwd__
keyboard=comm.keyboard
_http=comm._http
colorize_label=comm.colorize_label
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources' ))
IMAGES_PATH = xbmc.translatePath(os.path.join(__resource__, 'media'))
__subpath__  = xbmc.translatePath( os.path.join( __cwd__, 'subtitles') ).decode("utf-8")
if not os.path.exists(__subpath__):
	os.makedirs(__subpath__)
__temppath__  = xbmc.translatePath( os.path.join( __cwd__, 'temp') ).decode("utf-8")
if not os.path.exists(__temppath__):
	os.makedirs(__temppath__)
videoexts=plugin.get_setting('videoext').lower().split(',')
musicexts=plugin.get_setting('musicext').lower().split(',')

cookiefile = xbmc.translatePath(os.path.join(__cwd__, 'cookie.dat'))
subcache = plugin.get_storage('subcache')
ids = plugin.get_storage('ids')
renameext = plugin.get_storage('renameext')
cursorttype= plugin.get_storage('cursorttype')
if not cursorttype.raw_dict().has_key('s'):
	cursorttype['s']='0'

import magnet
import douban
import javbus



class QRShower(xbmcgui.WindowDialog):
	def __init__(self):
		# width=self.getWidth()
		# height=self.getHeight()
		imgsize=360
		bkimg  = xbmc.translatePath( os.path.join( IMAGES_PATH, 'select-bg.png') )
		bkimgControl = xbmcgui.ControlImage(0,0,1280,720, filename = bkimg)
		self.addControl(bkimgControl)
		self.imgControl = xbmcgui.ControlImage((1280-imgsize)/2, (720-imgsize)/2,imgsize, imgsize, filename = '')
		self.addControl(self.imgControl)
		self.labelControl = xbmcgui.ControlLabel((1280-imgsize)/2, (720+imgsize)/2 + 10, imgsize, 10, '请用115手机客户端扫描二维码', alignment = 0x00000002)
		self.addControl(self.labelControl)

	def showQR(self, url):
		socket = urllib.urlopen( url )
		pngdata = socket.read()
		qrfilepath=xbmc.translatePath( os.path.join( __temppath__, 'qr%s.png'%(uuid.uuid4().hex)) ).decode('utf-8')
		with open(qrfilepath, "wb") as qrFile:
			qrFile.write(pngdata)
		qrFile.close()
		self.imgControl.setImage(qrfilepath)
		self.doModal()
		
	def changeLabel(self, label):
		self.labelControl.setLabel(label)
	def onAction(self,action):
		self.close()
	def onClick(self, controlId):
		self.close()
		
class PassRedirectHandler(urllib2.HTTPRedirectHandler):
	def http_error_301(self, req, fp, code, msg, headers): 
		infourl = urllib.addinfourl(fp, headers, req.get_full_url())
		infourl.status = code
		infourl.code = code
		return infourl
		
	def http_error_302(self, req, fp, code, msg, headers):
		infourl = urllib.addinfourl(fp, headers, req.get_full_url())
		infourl.status = code
		infourl.code = code
		return infourl
		
class api_115(object):
	bad_servers = ['fscdnuni-vip.115.com', 'fscdntel-vip.115.com','cdnuni.115.com']
	is_vip=0
	user_name=''
	def __init__(self, cookiefile):
		
		self.cookiejar = cookielib.LWPCookieJar()
		try:
			if os.path.exists(cookiefile):
				self.cookiejar.load(
					cookiefile, ignore_discard=True, ignore_expires=True)
				
			self.opener = urllib2.build_opener(
				urllib2.HTTPCookieProcessor(self.cookiejar))
		except:
			os.remove(cookiefile)
		self.headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36',
			'Accept-encoding': 'gzip,deflate',
		}

	def islogin(self):
		try:
			data = self.urlopen('https://my.115.com/?ct=ajax&ac=nav&_=' + str(time.time()))
			data = self.fetch(data)
			data = json.loads(data[data.index('{'):])
			if data['state'] != True:
				return {'state':False, 'message':data['msg']}
			if data['data'].has_key('user_name'):
				self.user_name = data['data']['user_name']
			else:
				self.user_name = data['data']['user_id']
			self.is_vip=0
			if data['data'].has_key('vip'):
				self.is_vip=data['data']['vip']
			
			return True
		except:
			return False
		
	def login(self):
		try:
			#opener = urllib2.build_opener()
			#login_page = opener.open('http://qrcodeapi.115.com/api/1.0/web/1.0/token')
			self.cookiejar = cookielib.LWPCookieJar()
			self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
			login_page = self.urlopen('http://qrcodeapi.115.com/api/1.0/web/1.0/token')
			msgs=json.loads(self.fetch(login_page))
			uid,_t,sign=msgs['data']['uid'],msgs['data']['time'],msgs['data']['sign']
			
		except:
			return {'state':False, 'message':'Login Error'}
		
		qrcode_url='http://qrcodeapi.115.com/api/1.0/web/1.0/qrcode?qrfrom=1&&uid='+str(uid)+'&_t='+str(time.time())
		
		qrShower = QRShower()
		#qrShower.showQR(qrcode_url)
		qthread = threading.Thread(target=qrShower.showQR, args=(qrcode_url,))
		qthread.start()
		
		for i in range(3):
			try:
				data = self.urlopen('http://qrcodeapi.115.com/get/status/?uid='+str(uid)+'&sign='+str(sign)+'&time='+str(_t)+'&_t='+str(long(time.time())))
			except Exception, e:
				qrShower.close()
				qthread.join()
				return {'state':False, 'message':'Login Error'}
			ll = json.loads(self.fetch(data))
			
		qrShower.close()
		for f in os.listdir(__temppath__):
			if re.search(r'^qr.*',f):
				os.remove( os.path.join( __temppath__, f).decode('utf-8'))
		qthread.join()
		try:
			data = self.urlopen('http://passportapi.115.com/app/1.0/web/1.0/login/qrcode',data='app=web&account=' + str(uid))
			data = self.fetch(data)
			if self.islogin():
				if os.path.exists(cookiefile):
					os.remove(cookiefile)
				self.cookiejar.save(cookiefile, ignore_discard=True)
				return {'state':True, 'user_name':self.user_name,'is_vip':self.is_vip}
			else:
				return  {'state':False, 'message':'Login Error'}
		except:
			return {'state':False, 'message':'Login Error'}
			
	def loginold(self):
		try:
			login_page = self.urlopen('http://passport.115.com/?ct=login&ac=qrcode_token&is_ssl=1')
			msgs=json.loads(self.fetch(login_page))
			uid,_t,sign=msgs['uid'],msgs['time'],msgs['sign']
			
			sessionid_page=self.urlopen('http://msg.115.com/proapi/anonymous.php?ac=signin&user_id='+str(uid)+'&sign='+str(sign)+'&time='+str(_t))
			sessionmsgs=json.loads(self.fetch(sessionid_page))
			sessionid=sessionmsgs['session_id']
			imserver = sessionmsgs['server']
		except:
			return {'state':False, 'message':'Login Error'}
		qrcode_url='http://dgqrcode.115.com/api/qrcode.php?qrfrom=1&&uid='+str(uid)+'&_t='+str(time.time())
		
		qrShower = QRShower()
		#qrShower.showQR(qrcode_url)
		qthread = threading.Thread(target=qrShower.showQR, args=(qrcode_url,))
		qthread.start()
		
		for i in range(2):
			try:
				data = self.urlopen('http://'+imserver+'/chat/r?VER=2&c=b0&s='+str(sessionid)+'&_t='+str(long(time.time())))
			except Exception, e:
				qrShower.close()
				qthread.join()
				return {'state':False, 'message':'Login Error'}
			ll = json.loads(self.fetch(data))
			#ll = eval(data)
			#ll = json.loads(data[data.index('[{'):])
			for l in ll:
				for p in l['p']:
					if p.has_key('key') == False:
						#qrShower.changeLabel('请在手机客户端点击登录确认')
						continue
					key = p['key']
					v = p['v']
					break;
		if key is None:
			return {'state':False, 'message':'Login Error'}
		qrShower.close()
		qthread.join()
		try:
			data = self.urlopen('http://fspassport.115.com/?ct=login&ac=qrcode&key=' + key + '&v=' + v)
			data = self.fetch(data)
			if self.islogin():
				if os.path.exists(cookiefile):
					os.remove(cookiefile)
				self.cookiejar.save(cookiefile, ignore_discard=True)
				return {'state':True, 'user_name':self.user_name,'is_vip':self.is_vip}
			else:
				return  {'state':False, 'message':'Login Error'}
		except:
			return {'state':False, 'message':'Login Error'}
			
	def urlgetlocation(self,url):
		headers=self.headers.copy()
		headers.update({'Range':'bytes=0-10'})
		request = urllib2.Request(url,headers=headers)
		#request.get_method = lambda : 'HEAD'
		try:
			opener2 = urllib2.build_opener(PassRedirectHandler)
			rs = opener2.open(request)
			return rs
		except:
			return ''
		
	def urlopen(self, url, **args): 
		#plugin.log.error(url)
		if 'cookie' in args:
			cookiename,cookievalue=args['cookie'].split('=')
			cook=self.make_cookie(cookiename, cookievalue, '.115.com')
			
			self.cookiejar.set_cookie(cook)
			del args['cookie']
			
		if 'data' in args and type(args['data']) == dict:
			args['data'] = json.dumps(args['data'])
			self.headers['Content-Type'] = 'application/json'
		else:
			self.headers['Content-Type'] = 'application/x-www-form-urlencoded'
		try:
			headers=self.headers.copy()
			
			if url.find('|')>0:
				url,head=url.split('|')
				params_dict=urlparse.parse_qsl(head)
				params = dict(params_dict)
				headers.update(params)
			rs = self.opener.open(
				urllib2.Request(url, headers=headers, **args), timeout=60)
			#plugin.log.error('zzzdebug:%s'%rs.fp._sock)
			return rs
		except Exception, e:
			plugin.log.error('zzzdebug:%s'%e)
			return ''
			
	def jsonload(self,data):
		try:
			data= self.fetch(data).replace('\n','').replace('\r','')
			data=json.loads(data[data.index('{'):])
			return data
		except:
			return {'state':False}
			
	def getfilelist(self,cid,offset,pageitem,star,sorttype,sortasc,typefilter='0',nf='0',search_value=''):
		if search_value!='' and search_value!='0':
			data=urllib.urlencode({'search_value': search_value,'cid':cid,'aid':'1','limit':str(pageitem),
							'offset':str(offset),'format':'json','date':'','pick_code':'','type':typefilter,'source':''})
			data=self.urlopen('http://web.api.115.com/files/search?'+data)
		else:	
			data = urllib.urlencode({'aid': '1','cid':cid,'limit':pageitem,'offset':offset,'type':typefilter,'star':star,'custom_order':'2',
								'o':sorttype,'asc':sortasc,'nf':nf,'show_dir':'1','format':'json','_':str(long(time.time()))})
			if sorttype=='file_name':
				data=self.urlopen('http://aps.115.com/natsort/files.php?'+data)
			else:
				data=self.urlopen('http://web.api.115.com/files?'+data)
		
		return self.jsonload(data)
	
	def offline(self,url):
		uid = self.getcookieatt('.115.com', 'UID')
		uid = uid[:uid.index('_')]
		data = urllib.urlencode({'url': url,'uid':uid,'time':str(long(time.time()))})
		data=self.urlopen("http://115.com/web/lixian/?ct=lixian&ac=add_task_url",data=data)
		data=self.fetch(data)
		data=json.loads(data[data.index('{'):])
		return data
		
	def offline_list(self):
		uid = self.getcookieatt('.115.com', 'UID')
		uid = uid[:uid.index('_')]
		page=1
		task=[]
		while True:
			data = urllib.urlencode({'page': str(page),'uid':uid,'time':str(long(time.time()))})
			data=self.urlopen("http://115.com/web/lixian/?ct=lixian&ac=task_lists",data=data)
			data=self.fetch(data)
			data=json.loads(data[data.index('{'):])
			if data['state'] and data['tasks']:
				for item in data['tasks']:
					task.append(item)
				if data['page_count']>page:
					page=page+1
				else:
					break
			else:
				break
		return task
		
	def rename(self,fid,newname):
		data = urllib.urlencode({'fid': fid,'file_name':newname})
		try:
			data=self.urlopen('http://web.api.115.com/files/edit',data=data)
			data= self.fetch(data).replace('\n','').replace('\r','')
			data=json.loads(data[data.index('{'):])
			return data['state']
		except:
			return False
			
	def getcookiesstr(self):
		cookies=''
		try:
			for k,v in self.cookiejar._cookies['.115.com']['/'].items():
				cookies+=str(k)+'='+str(v.value)+';'
			cookies=urllib.quote_plus(cookies)
			return cookies
		except:
			return ''

	def getfiledownloadurl(self,pc,changeserver='',withcookie=False):
		result = ''
		data=self.urlopen("https://webapi.115.com/files/download?pickcode="+pc+"&_="+str(long(time.time())))
		if 'Set-Cookie' in data.headers:
			downcookies = re.findall(r"[0-9abcdef]{20,}\s*\x3D\s*[0-9abcdef]{20,}", data.headers['Set-Cookie'], re.DOTALL | re.MULTILINE)
			'''
			downcookies=data.headers['Set-Cookie'].split(',')
			'''
			self.downcookie=''
			for downcook in downcookies:
				self.downcookie+=downcook
			
		data= self.jsonload(data)
		if data['state']:
			result=data['file_url']
		if not result:
			data=self.urlopen("http://proapi.115.com/app/chrome/down?method=get_file_url&pickcode="+pc)
			data= self.jsonload(data)
			if data['state']:
				for value in data['data'].values():
					if value.has_key('url'):
						result = value['url']['url']
						break
		if not result:
			return ''
		#if result.find('down_group')>0:
			#changeserver=False
		if changeserver!='' and changeserver!='0':
			result = re.sub('(http://)(.*115.com)(.*)', r'\1'+changeserver+r'\3', result)
		
		#if result.find('down_group')>0:
			#plugin.notify('aaa')
			#return result
		
		if withcookie:
			cookies=''
			try:
				for k,v in self.cookiejar._cookies['.115.com']['/'].items():
					cookies+=str(k)+'='+str(v.value)+';'
				cookies+=self.downcookie+';'
				#cookies=urllib.quote_plus(cookies)
			except:
				os.remove(cookiefile)
			#return result+'|Cookie='+cookies
			#return result+'&'+cookies
			headers=self.headers.copy()
			headers.update({'Cookie':cookies})
			result=result+'|'+urllib.urlencode(headers)
		
		return result
		
	def fetch(self,wstream):
		if wstream=='':
			return ''
		try:
			if wstream.headers.get('content-encoding', '') == 'gzip':
				content = gzip.GzipFile(fileobj=StringIO(wstream.read())).read()
			else:
				content = wstream.read()
			return content
		except:
			return ''
			
	def make_cookie(self, name, value, domain, path='/'):
		return cookielib.Cookie(
			version=0, 
			name=name, 
			value=value,
			port=None, 
			port_specified=False,
			domain=domain, 
			domain_specified=True, 
			domain_initial_dot=False,
			path=path, 
			path_specified=True,
			secure=False,
			expires=None,
			discard=False,
			comment=None,
			comment_url=None,
			rest=None
		)
	
	def getcookieatt(self, domain, attr):
		if domain in self.cookiejar._cookies and attr in \
		   self.cookiejar._cookies[domain]['/']:
			return self.cookiejar._cookies[domain]['/'][attr].value
			
	def depass(self,ac,ps,co):
		eac=hashlib.sha1(ac).hexdigest()
		eps=hashlib.sha1(ps).hexdigest()
		return hashlib.sha1(hashlib.sha1(eps+eac).hexdigest()+co.upper()).hexdigest()

	def encodes(self):
		prefix = ""
		phpjs=int(random.random() * 0x75bcd15)
		retId = prefix
		retId += self.encodess(int(time.time()),8)
		retId += self.encodess(phpjs, 5)
		return retId

	def encodess(self,seed, reqWidth):
		seed = hex(int(seed))[2:]
		if (reqWidth < len(seed)):
			return seed[len(seed) - reqWidth:]
		if (reqWidth >  len(seed)):
			return (1 + (reqWidth - seed.length)).join('0') + seed
		return seed
		

xl = api_115(cookiefile)

class CaptchaDlg(xbmcgui.WindowDialog):
	def __init__(self):
		# width=self.getWidth()
		# height=self.getHeight()
		bkimg  = xbmc.translatePath( os.path.join( IMAGES_PATH, 'select-bg.png') )
		bkimgControl = xbmcgui.ControlImage(0,0,1280,720, filename = bkimg)
		self.addControl(bkimgControl)
		
		self.capimg = xbmcgui.ControlImage(640-100, 160,200, 50, filename = '')
		self.addControl(self.capimg)
		self.buttonreset = xbmcgui.ControlButton(640+100, 160, 100, 40, 'reset')
		self.addControl(self.buttonreset)
		
		self.capimg1 = xbmcgui.ControlImage(640-100, 210,50, 50, filename = '')
		self.addControl(self.capimg1)
		self.capimg2 = xbmcgui.ControlImage(640-50, 210,50, 50, filename = '')
		self.addControl(self.capimg2)
		self.capimg3 = xbmcgui.ControlImage(640-0, 210,50, 50, filename = '')
		self.addControl(self.capimg3)
		self.capimg4 = xbmcgui.ControlImage(640+50, 210,50, 50, filename = '')
		self.addControl(self.capimg4)
		
		self.capallimg = xbmcgui.ControlImage(640-125,360,250, 100, filename = '')
		self.addControl(self.capallimg)
		
		self.button0 = xbmcgui.ControlButton(640-125+5, 320, 40, 40, '0')
		self.addControl(self.button0)
		self.button1 = xbmcgui.ControlButton(640-75+5, 320, 40, 40, '1')
		self.addControl(self.button1)
		self.button2 = xbmcgui.ControlButton(640-25+5, 320, 40, 40, '2')
		self.addControl(self.button2)
		self.button3 = xbmcgui.ControlButton(640+25+5, 320, 40, 40, '3')
		self.addControl(self.button3)
		self.button4 = xbmcgui.ControlButton(640+75+5, 320, 40, 40, '4')
		self.addControl(self.button4)
		
		self.button5 = xbmcgui.ControlButton(640-125+5, 460, 40, 40, '5')
		self.addControl(self.button5)
		self.button6 = xbmcgui.ControlButton(640-75+5, 460, 40, 40, '6')
		self.addControl(self.button6)
		self.button7 = xbmcgui.ControlButton(640-25+5, 460, 40, 40, '7')
		self.addControl(self.button7)
		self.button8 = xbmcgui.ControlButton(640+25+5, 460, 40, 40, '8')
		self.addControl(self.button8)
		self.button9 = xbmcgui.ControlButton(640+75+5, 460, 40, 40, '9')
		self.addControl(self.button9)
		
		data = xl.urlopen('https://captchaapi.115.com/?ac=security_code&type=web')
		if 'Set-Cookie' in data.headers:
			signs = re.findall(r'[0-9a-z]{26}', data.headers['Set-Cookie'], re.DOTALL | re.MULTILINE)
			if len( signs)>=1:
				self.sign=signs[0]
				
		self.showcap()
		
	def showcap(self):
		#capemptyfilepath=xbmc.translatePath( os.path.join( IMAGES_PATH, 'capempty.png') ).decode('utf-8')
		#self.capimg.setImage(capemptyfilepath,useCache=False)
		
		socket = xl.urlopen( 'https://captchaapi.115.com/?ct=index&ac=code',cookie='PHPSESSID='+self.sign)
		pngdata = socket.read()
		capfilepath=xbmc.translatePath( os.path.join( __temppath__, 'cap%s.png'%(uuid.uuid4().hex)) ).decode('utf-8')
		with open(capfilepath, "wb") as capFile:
			capFile.write(pngdata)
		capFile.close()
		self.capimg.setImage(capfilepath,useCache=False)
		#os.remove(capfilepath)
		#self.capimg.setImage('https://captchaapi.115.com/?ct=index&ac=code',useCache=False)
		socket = xl.urlopen( 'https://captchaapi.115.com/?ct=index&ac=code&t=all',cookie='PHPSESSID='+self.sign)
		pngdata = socket.read()
		capallfilepath=xbmc.translatePath( os.path.join( __temppath__, 'capall%s.png'%(uuid.uuid4().hex)) ).decode('utf-8')
		with open(capallfilepath, "wb") as capallFile:
			capallFile.write(pngdata)
		capallFile.close()
		self.capallimg.setImage(capallfilepath,useCache=False)
		
		capemptyfilepath=xbmc.translatePath( os.path.join( IMAGES_PATH, 'capempty.png') ).decode('utf-8')
		self.capimg1.setImage(capemptyfilepath)
		self.capimg2.setImage(capemptyfilepath)
		self.capimg3.setImage(capemptyfilepath)
		self.capimg4.setImage(capemptyfilepath)
		self.caplist=[-1,-1,-1,-1]
		
	def onControl(self,controlId):
		if controlId==self.buttonreset:
			self.showcap()
			return
			
		selectval=-1
		
		if controlId==self.button0:
			selectval=0
		if controlId==self.button1:
			selectval=1
		if controlId==self.button2:
			selectval=2
		if controlId==self.button3:
			selectval=3
		if controlId==self.button4:
			selectval=4
		if controlId==self.button5:
			selectval=5
		if controlId==self.button6:
			selectval=6
		if controlId==self.button7:
			selectval=7
		if controlId==self.button8:
			selectval=8
		if controlId==self.button9:
			selectval=9
			
		if selectval>=0:
			if self.caplist[0]==-1:
				self.caplist[0]=selectval
				socket = xl.urlopen('https://captchaapi.115.com/?ct=index&ac=code&t=single&id=%s'%(selectval),cookie='PHPSESSID='+self.sign)
				pngdata = socket.read()
				cap1filepath=xbmc.translatePath( os.path.join( __temppath__, 'cap1%s.png'%(uuid.uuid4().hex)) ).decode('utf-8')
				with open(cap1filepath, "wb") as cap1file:
					cap1file.write(pngdata)
				cap1file.close()
				self.capimg1.setImage(cap1filepath,useCache=False)
			elif self.caplist[1]==-1:
				self.caplist[1]=selectval
				socket = xl.urlopen('https://captchaapi.115.com/?ct=index&ac=code&t=single&id=%s'%(selectval),cookie='PHPSESSID='+self.sign)
				pngdata = socket.read()
				cap2filepath=xbmc.translatePath( os.path.join( __temppath__, 'cap2%s.png'%(uuid.uuid4().hex)) ).decode('utf-8')
				with open(cap2filepath, "wb") as cap2file:
					cap2file.write(pngdata)
				cap2file.close()
				self.capimg2.setImage(cap2filepath,useCache=False)
			elif self.caplist[2]==-1:
				self.caplist[2]=selectval
				socket = xl.urlopen('https://captchaapi.115.com/?ct=index&ac=code&t=single&id=%s'%(selectval),cookie='PHPSESSID='+self.sign)
				pngdata = socket.read()
				cap3filepath=xbmc.translatePath( os.path.join( __temppath__, 'cap3%s.png'%(uuid.uuid4().hex)) ).decode('utf-8')
				with open(cap3filepath, "wb") as cap3file:
					cap3file.write(pngdata)
				cap3file.close()
				self.capimg3.setImage(cap3filepath,useCache=False)
			elif self.caplist[3]==-1:
				self.caplist[3]=selectval
				socket = xl.urlopen('https://captchaapi.115.com/?ct=index&ac=code&t=single&id=%s'%(selectval),cookie='PHPSESSID='+self.sign)
				pngdata = socket.read()
				cap4filepath=xbmc.translatePath( os.path.join( __temppath__, 'cap4%s.png'%(uuid.uuid4().hex)) ).decode('utf-8')
				with open(cap4filepath, "wb") as cap4file:
					cap4file.write(pngdata)
				cap4file.close()
				self.capimg4.setImage(cap4filepath,useCache=False)
				
				code='%s%s%s%s'%(self.caplist[0],self.caplist[1],self.caplist[2],self.caplist[3])
				data = xl.urlopen('https://webapi.115.com/user/captcha',data='code=%s&sign=%s&ac=security_code&type=web'%(code,self.sign))
				data=xl.jsonload(data)
				if data['state']:
					plugin.notify('验证通过')
					for f in os.listdir(__temppath__):
						if re.search(r'^cap.*',f):
							os.remove( os.path.join( __temppath__, f).decode('utf-8'))
					self.close()
				else:
					self.showcap()
		
'''
class MyPlayer(xbmc.Player):
	def __init__(self):
		xbmc.Player.__init__(self)

	def onPlayBackEnded(self):
		renavitoext()
		xbmc.Player.onPlayBackEnded(self)

	def onPlayBackStopped(self):
		renameext.clear()
		renavitoext()

player = MyPlayer()
'''
@plugin.route('/login')
def login():
	r=xl.login()
	if r['state']:
		msg='登录成功!当前用户：'+r['user_name']
		if r['is_vip']!=1:
			msg=msg+' 您还不是VIP用户，某些功能可能无法使用，请谅解。'
		plugin.notify(msg=msg)
	else:
		plugin.notify('登录失败：' + r['message'])
	return

@plugin.route('/setting')
def setting():
	ret= plugin.open_settings()
	return

@plugin.route('/')
def index():
	#pageresult = _http('http://nanrencili.vip/list/%E4%B8%89%E4%B8%8A%E6%82%A0%E4%BA%9A/4/2/0.html')
	#html_parser = HTMLParser.HTMLParser()
	#pageresult=html_parser.unescape(pageresult)
	#plugin.log.error(pageresult)
	items = [
		{'label': '网盘文件', 'path': plugin.url_for('getfilelist',cid='0',offset=0,star='0',typefilter=0,searchstr='0',changesort='0'),'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'icon.png') )},
		{'label': '星标列表', 'path': plugin.url_for('getfilelist',cid='0',offset=0,star='1',typefilter=0,searchstr='0',changesort='0'),'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'star.png') )},
		{'label': '离线任务列表', 'path': plugin.url_for('offline_list'),'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'offlinedown.png') )},
		#{'label': '网盘搜索', 'path': plugin.url_for('search',cid='0',mstr='0',offset=0),'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'disksearch.png') )},
		{'label': '搜索', 'path': plugin.url_for('searchinit',stypes='pan,bt,db,jav',sstr='0',modify='0',otherargs='{}'),'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'disksearch.png') )},
		#{'label': '磁力搜索', 'path': plugin.url_for('btsearchother',sstr='0', modify='0'),'thumbnail':xbmc.translatePath(os.path.join( IMAGES_PATH, 'magnet.png'))},
		{'label': '豆瓣标签', 'path': plugin.url_for('dbmovie',tags='0',sort='U',page='0',addtag='0',scorerange='0',year_range='0'),
							'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'douban.png') )},
		#{'label': '豆瓣电影搜索', 'path': plugin.url_for('dbactor', sstr='0', page=0),'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'moviesearch.png') )},
		{'label': '豆瓣排行榜', 'path': plugin.url_for('dbtops'),'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'topmovies.png') )},
		{'label': '扫码登入', 'path': plugin.url_for('login'),'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'scan.png') )},
		{'label': '设置', 'path': plugin.url_for('setting'),'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'setup.png') )},
		{'label': '清空tempplay', 'path': plugin.url_for('cleartempplay')},
		#{'label': 'captcha', 'path': plugin.url_for('captcha')},
	]
	if str(plugin.get_setting('javbus'))=='true':
		items.insert(7, {'label': 'javbus', 'path': plugin.url_for('javbus'),'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'javbus.png') ).decode('utf-8')})
	sortasc=str(plugin.get_setting('sortasc'))
	setthumbnail['set']=True
	
	return items

@plugin.route('/btsearchother')
def btsearchother():
	comm.moviepoint['group']='other'
	comm.moviepoint['thumbnail']='0'
	return magnet.btsearchInit(sstr='0', modify='0')

def stypesearch(liststypes,sstr,dictotherargs):
	stypedict={'pan':'网盘搜索','bt':'磁力搜索','db':'豆瓣搜索','jav':'JAVBUS搜索'}
	stype=''
	if len(liststypes)==1:
		stype=liststypes[0]
	else:
		dialog = xbmcgui.Dialog()
		selectlist=[]
		for st in liststypes:
			selectlist.append((st,stypedict[st]))
		sel = dialog.select('搜索'+colorize_label(sstr, color='FFFF00'), [q[1] for q in selectlist])
		if sel>=0:
			stype= selectlist[sel][0]
			
	if stype=='pan':
		cid='0'
		if dictotherargs.has_key('cid'):
			cid=dictotherargs['cid']
		#return pansearch(cid=cid,mstr=sstr,offset=0)
		return getfilelist(cid=cid,offset=0,star='0',typefilter='0',searchstr=sstr,changesort='0')
	elif stype=='bt':
		return magnet.btsearchInit(sstr=sstr, modify='0')
	elif stype=='db':
		return douban.dbsearch(sstr=sstr, page=0)
	elif stype=='jav':
		qbbblist=[('骑兵','qb'),('步兵','bb'),('好雷屋','om')]
		dialog = xbmcgui.Dialog()
		sel = dialog.select('JAVBUS 搜索'+colorize_label(sstr, color='FFFF00'),[q[0] for q in qbbblist])
		if sel>=0:
			qbbb= qbbblist[sel][1]
			return javbus.javlist(qbbb=qbbb,filtertype='search',filterkey=sstr,page=1)

def selectstr(sstr):
	strlist=re.split(r'[\s\x2E\x5B\x5D\x28\x29\x3C\x3E\x5F]+', sstr)
	plugin.notify(strlist)
	strsel=''
	dialog = xbmcgui.Dialog()
	sel=999
	while sel>0:
		sellist=['选择：'+colorize_label(strsel, color='FFFF00')]+strlist
		sel = dialog.select('选择字符串',sellist)
		if sel>0:
			strsel=strsel+' '+strlist[sel-1]
			strsel=strsel.strip()
			strlist.pop(sel-1)
		if sel==-1:
			strsel=''
	return strsel

@plugin.route('/searchinit/<stypes>/<sstr>/<modify>/<otherargs>')
def searchinit(stypes,sstr,modify,otherargs):
	if not comm.searchvalues.raw_dict().has_key('strlist'):
		comm.searchvalues['strlist']=[]
	sstr=sstr.strip()
	liststypes=stypes.split(',')
	if str(plugin.get_setting('javbus'))!='true':
		if 'jav' in liststypes:
			liststypes.remove('jav')
	dictotherargs=json.loads(otherargs)
	if not isinstance(dictotherargs,dict):
		dictotherargs={}
	if sstr and sstr!='0' and modify=='0':
		comm.searchvalues['strlist']= [e for e in comm.searchvalues['strlist'] if e!=sstr]
		comm.searchvalues['strlist'].append(sstr)
		return stypesearch(liststypes,sstr,dictotherargs)
	else:
		if modify=='1':
			if sstr=='0': sstr=''
			newsstr = keyboard(text=sstr).strip()
			if not newsstr:
				return
			comm.searchvalues['strlist']= [e for e in comm.searchvalues['strlist'] if e!=sstr]
			comm.searchvalues['strlist']= [e for e in comm.searchvalues['strlist'] if e!=newsstr]
			#comm.searchvalues['strlist'].append(newsstr)
			if not sstr:
				comm.searchvalues['strlist'].append(newsstr)
				return stypesearch(liststypes,newsstr,dictotherargs)
			else:
				xbmc.executebuiltin('Container.update('+plugin.url_for('searchinit',stypes=stypes,sstr=newsstr,modify='0',otherargs=otherargs)+')')
			return
		if modify=='4':
			newsstr=selectstr(sstr)
			if not newsstr:
				return
			comm.searchvalues['strlist']= [e for e in comm.searchvalues['strlist'] if e!=newsstr]
			xbmc.executebuiltin('Container.update('+plugin.url_for('searchinit',stypes=stypes,sstr=newsstr,modify='0',otherargs=otherargs)+')')
		if modify=='2':
			comm.searchvalues['strlist']= [e for e in comm.searchvalues['strlist'] if e!=sstr]
			xbmc.executebuiltin('Container.Refresh()')
			return
		if modify=='3':
			dialog = xbmcgui.Dialog()
			ret = dialog.yesno('清空搜索关键字', '是否删除所有搜索关键字')
			if ret:
				comm.searchvalues['strlist']=[]
		items=[]
		items.append({'label': colorize_label('添加搜索关键字', color='00FF00'), 'path': plugin.url_for('searchinit',stypes=stypes,sstr='0',modify='1',otherargs=otherargs)})
		for strvalue in comm.searchvalues['strlist'][::-1]:
			context_menu_items=[]
			listitem=ListItem(label=strvalue, label2=None, icon=None, thumbnail=None, 
					path=plugin.url_for('searchinit',stypes=stypes,sstr=strvalue.encode('utf-8'),modify='0',otherargs=otherargs))
			context_menu_items.append(('编辑关键字'+colorize_label(strvalue, color='0000FF'), 'RunPlugin('+plugin.url_for('searchinit',stypes=stypes,sstr=strvalue.encode('utf-8'),modify='1',otherargs=otherargs)+')',))
			context_menu_items.append(('删除关键字'+colorize_label(strvalue, color='FF0000'), 'RunPlugin('+plugin.url_for('searchinit',stypes=stypes,sstr=strvalue.encode('utf-8'),modify='2',otherargs=otherargs)+')',))
			if len(context_menu_items)>0:
				listitem.add_context_menu_items(context_menu_items,False)
			items.append(listitem)
		if len(comm.searchvalues['strlist'])>0:
			items.append({'label': colorize_label('清空搜索关键字', color='FF0000'), 'path': plugin.url_for('searchinit',stypes=stypes,sstr='0',modify='3',otherargs=otherargs)})
		return items

@plugin.route('/pansearch/<cid>/<mstr>/<offset>')
def pansearch(cid,mstr,offset):
	if not mstr or mstr=='0':
		mstr = keyboard()
		if not mstr:
			return
	data=getfilelistdata(cid,offset,'0','0',searchstr=mstr)
	if data['state']:
		#playlistvideo = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
		#playlistvideo.clear()
		
		imagecount=0
		items=[]
		
		milkname='115'
		
		if str(plugin.get_setting('genm3u8'))=='true':
			items.append({'label': '生成M3U8文件', 'path': plugin.url_for('m3u8',cid=cid,offset=offset,star='0',name=milkname.encode('utf-8'))})
		if str(plugin.get_setting('milkvr'))=='true':
			items.append({'label': '生成MilkVR文件', 'path': plugin.url_for('milkvr',cid=cid,offset=offset,star='0',name=milkname.encode('utf-8'))})
		
		for item in data['data']:
			listitem=getListItem(item,mstr)
			if listitem!=None:
				#if listitem.playable:
					#playlistvideo.add(listitem.get_path(), listitem.as_xbmc_listitem())
				items.append(listitem)
				if item.has_key('ms'):
					imagecount+=1
		if data['count']>int(offset)+int(pageitem):
			items.append({'label': colorize_label('下一页', 'next'),
				'path': plugin.url_for('pansearch',cid=cid,mstr=mstr,offset=str(int(offset)+int(pageitem))),
				'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'nextpage.png') ).decode('utf-8')})
			#urlcache[cid+"/"+offset+"/"+str(star)] = items
		#xbmc.executebuiltin('Container.SetViewMode(8)')
		#skindir=xbmc.getSkinDir()
		if imagecount >= 10 and imagecount * 2 > len(items):
			setthumbnail['set']=True
			#plugin.notify('setthumbnail')
			#if ALL_VIEW_CODES['thumbnail'].has_key(skindir):
			#	plugin.set_view_mode(ALL_VIEW_CODES['thumbnail'][skindir])
		return items
	else:
		plugin.notify(msg='数据获取失败,错误信息:'+str(data['error']))
		login()
		return
		
def is_subtitle(ext):
	return ext.lower() in ['srt', 'sub', 'ssa', 'smi', 'ass']
	
def getListItem(item,pathname=''):
	#plugin.log.error(item)
	context_menu_items=[]
	context_menu_items.append(('搜索'+colorize_label(item['n'].encode('UTF-8'), color='00FF00'), 
		'RunPlugin('+plugin.url_for('searchinit',stypes='pan,bt,db,jav',sstr=item['n'].encode('UTF-8'),modify='4',otherargs='0')+')',))
	if item.has_key('sha'):
		context_menu_items.append(('用'+colorize_label('浏览器','dir')+'打开代理链接', 
				'RunPlugin('+plugin.url_for('shellopen',pc=item['pc'],fname=item['n'].encode('UTF-8'))+')',))
		if item.has_key('iv'):
			isiso='1'
			if item.has_key('vdi'):
				if item['vdi']>=1:
					isiso='0'
			listitem=ListItem(label=colorize_label(item['n'], 'video'), label2=None, icon=None, thumbnail=None, 
					path=plugin.url_for('play',pc=item['pc'],name=item['n'].encode('UTF-8'),iso=isiso))
			
			listitem.set_info('video', {'title':item['n'],'size': item['s']})
			#listitem.as_xbmc_listitem().setContentLookup(False)
			listitem.set_is_playable('true')
			context_menu_items.append(('FFMpeg转码下载', 
				'RunPlugin('+plugin.url_for('ffmpeg',pc=item['pc'],name=item['n'].encode('UTF-8'))+')',))
			if str(plugin.get_setting('milkvr'))=='true':
				context_menu_items.append(('在'+colorize_label('SamsungVR','dir')+'打开', 
					'RunPlugin('+plugin.url_for('samsungvr',pc=item['pc'],fname=item['n'].encode('UTF-8'),pathname=pathname.encode('UTF-8'))+')',))
		elif item.has_key('ms'):
			#imgurl=getimgurl(item['pc'])
			listitem=ListItem(label=colorize_label(item['n'], 'image'), label2=None, icon=None, thumbnail=None, path=plugin.url_for('playimg',pc=item['pc'],name=item['n'].encode('UTF-8')))
			#listitem=ListItem(label=colorize_label(item['n'], 'image'), label2=None, icon=None, thumbnail=None, path=imgurl)
			#listitem.set_info('pictures', {"Title": item['n'] } )
			listitem.playable=False


		elif item['ico'] in videoexts:
			listitem=ListItem(label=colorize_label(item['n'], 'video'), label2=None, icon=None, thumbnail=None, path=plugin.url_for('play',pc=item['pc'],name=item['n'].encode('UTF-8'),iso='1'))
			listitem.set_info('video', {'title':item['n'],'size': item['s']})
			#listitem.as_xbmc_listitem().setContentLookup(False)
			listitem.set_is_playable('true')
			if str(plugin.get_setting('milkvr'))=='true':
				context_menu_items.append(('在'+colorize_label('SamsungVR','dir')+'打开',
					'RunPlugin('+plugin.url_for('samsungvr',pc=item['pc'],fname=item['n'].encode('UTF-8'),pathname=pathname.encode('UTF-8'))+')',))

		elif  item['ico'] in musicexts:
			listitem=ListItem(label=colorize_label(item['n'], 'audio'), label2=None, icon=None, thumbnail=None, path=plugin.url_for('play',pc=item['pc'],name=item['n'].encode('UTF-8'),iso='1'))
			listitem.set_info('audio', {'title':item['n'],'size': item['s']})
			listitem.playable=True

		elif item['ico']=='torrent':
			listitem=ListItem(label=colorize_label(item['n'], 'bt'), label2=None, icon=None, thumbnail=None, path=plugin.url_for('offline_bt',sha1=item['sha']))
		
		elif str(plugin.get_setting('showallfiles'))=='true':
			listitem=ListItem(label=item['n'], label2=None, icon=None, thumbnail=None)
		else:
			listitem=None
			
		if is_subtitle(item['ico']):
			subcache[item['n'].encode('UTF-8')]=item['pc']
		
		if item.has_key('u') and  listitem!=None:
			listitem.set_thumbnail(item['u'])
			
		if item.has_key('cid'):
			locateurl=plugin.url_for('getfilelist',cid=item['cid'],offset=0,star='0',typefilter=0,searchstr='0',changesort='0')
			context_menu_items.append((colorize_label('定位到所在目录','menu'), 'Container.update('+locateurl+')',))
		if str(plugin.get_setting('panedit'))=='true':
			if listitem!=None and item.has_key('cid') and item.has_key('fid'):
				warringmsg='是否删除文件:'+item['n'].encode('UTF-8')
				deleteurl=plugin.url_for('deletefile',pid=item['cid'],fid=item['fid'],warringmsg=warringmsg)
				context_menu_items.append((colorize_label('删除',color='FF0044'), 'RunPlugin('+deleteurl+')',))
	else:
		listitem=ListItem(label=colorize_label(item['n'], 'dir'), label2=None, icon=None, thumbnail=None, path=plugin.url_for('getfilelist',cid=item['cid'],offset=0,star='0',typefilter=0,searchstr='0',changesort='0'))
		
		if item.has_key('pid'):
			locateurl=plugin.url_for('getfilelist',cid=item['pid'],offset=0,star='0',typefilter=0,searchstr='0',changesort='0')
			context_menu_items.append((colorize_label('定位到所在目录','menu'), 'Container.update('+locateurl+')',))
			
		if str(plugin.get_setting('panedit'))=='true':
			if item.has_key('cid') and item.has_key('pid'):
				warringmsg='是否删除目录及其下所有文件:'+item['n'].encode('UTF-8')
				#listitem.add_context_menu_items([('删除', 'RunPlugin('+plugin.url_for('deletefile',pid=item['pid'],fid=item['cid'],warringmsg=warringmsg)+')',)],False)
				deleteurl=plugin.url_for('deletefile',pid=item['pid'],fid=item['cid'],warringmsg=warringmsg)
				context_menu_items.append((colorize_label('删除',color='FF0044'), 'RunPlugin('+deleteurl+')',))
	if item.has_key('m') and  listitem!=None:
		listitem.set_property('is_mark',str(item['m']))
		listitem.label=colorize_label('★', 'star'+str(item['m']))+listitem.label
		if item.has_key('fid'):
			fid=item['fid']
		else:
			fid=item['cid']
		if str(plugin.get_setting('panedit'))=='true':
			context_menu_items.append((colorize_label('重命名',color='0044FF'), 'RunPlugin('+plugin.url_for('rename',fid=fid,filename=item['n'].encode('UTF-8'))+')',))
			context_menu_items.append((colorize_label('移动..',color='00FF44'), 'RunPlugin('+plugin.url_for('move',fid=fid,filename=item['n'].encode('UTF-8'))+')',))
		if str(item['m'])=='0':
			#listitem.add_context_menu_items([('星标', 'RunPlugin('+plugin.url_for('mark',fid=fid,mark='1')+')',)],False)
			context_menu_items.append((colorize_label('星标',color='FFFF00'), 'RunPlugin('+plugin.url_for('mark',fid=fid,mark='1')+')',))
		else:
			#listitem.add_context_menu_items([('取消星标', 'RunPlugin('+plugin.url_for('mark',fid=fid,mark='0')+')',)],False)
			context_menu_items.append(('取消星标', 'RunPlugin('+plugin.url_for('mark',fid=fid,mark='0')+')',))

	if len(context_menu_items)>0 and listitem!=None:
		listitem.add_context_menu_items(context_menu_items,False)
	return listitem

@plugin.route('/deletefile/<pid>/<fid>/<warringmsg>')
def deletefile(pid,fid,warringmsg):
	dialog = xbmcgui.Dialog()
	ret = dialog.yesno(colorize_label('删除警告',color='FF0044'), warringmsg)
	if ret:
		try:
			data = urllib.urlencode({'pid': pid,'fid':fid})	
			data=xl.urlopen('http://web.api.115.com/rb/delete',data=data)
			data= xl.fetch(data).replace('\n','').replace('\r','')
			data=json.loads(data[data.index('{'):])
			#plugin.notify(data,delay=50000)
			if data['state']:
				xbmc.executebuiltin('Container.Refresh()')
			else:
				plugin.notify(msg='删除失败,错误信息:'+str(data['error']))
				return
		except:
			plugin.notify(msg='删除失败')
			return

@plugin.route('/mark/<fid>/<mark>')
def mark(fid,mark):
	data = urllib.urlencode({'fid': fid,'is_mark':mark})
	try:
		data=xl.urlopen('http://web.api.115.com/files/edit',data=data)
		data= xl.fetch(data).replace('\n','').replace('\r','')
		data=json.loads(data[data.index('{'):])
		if data['state']:
			xbmc.executebuiltin('Container.Refresh()')
		else:
			plugin.notify(msg='星标失败,错误信息:'+str(data['error']))
			return
	except:
			plugin.notify(msg='星标失败')
			return


@plugin.route('/rename/<fid>/<filename>')
def rename(fid,filename):
	newname = keyboard(text=filename)
	if not newname:
		return
	if newname==filename:
		return
	result = xl.rename(fid,newname)	
	if result:
		xbmc.executebuiltin('Container.Refresh()')
	else:
		plugin.notify(msg='重命名失败')
		

def getdirinfo(cid):
	pageitems = {'0': 25,'1': 50,'2': 100}
	pageitem=pageitems[plugin.get_setting('pageitem')]
	offset=0
	data=getfilelistdata(cid,offset,'0','0',searchstr='0',nf='1')
	dirinfo={}
	dirinfo['state']=data['state']
	
	if data['state']:
		dirinfo['path']=[]
		for item in data['path']:
			if item['cid']==0:
				dirinfo['path'].append((0,'ROOT'))
			else:
				dirinfo['path'].append((item['cid'],item['name']))
		dirinfo['subdirs']=[]
		for item in data['data']:
			dirinfo['subdirs'].append((item['cid'],item['n']))
		offset+=pageitem
		while data['count']>offset:
			data=getfilelistdata(cid,offset,'0','0',searchstr='0',nf='1')
			offset+=pageitem
			if data['state']:
				for item in data['data']:
					dirinfo['subdirs'].append((item['cid'],item['n']))
			else:
				break;
	return dirinfo

def createdir(pid,cname):
	cname = keyboard(text=cname)
	if not cname:
		return pid
	data = urllib.urlencode({'pid': pid,'cname':cname})
	try:
		data=xl.urlopen('http://web.api.115.com/files/add',data=data)
		data= xl.fetch(data).replace('\n','').replace('\r','')
		data=json.loads(data[data.index('{'):])
		if data['state']:
			return data['cid']
		else:
			plugin.notify(msg='新建文件夹失败,错误信息:'+str(data['error']))
			return pid
	except:
			plugin.notify(msg='新建文件夹失败')
			return pid

def getdir(cid,title):
	sel=-1;
	dialog = xbmcgui.Dialog()
	while True:
		dirinfo=getdirinfo(cid)
		if dirinfo['state']:
			selectlist=[]
			
			#dirname=''
			for item in dirinfo['path']:
				#dirname+=item[1]+'\\'
				if item[0]!=cid:
					selectlist.append((item[0],colorize_label('返回到【'+item[1]+'】',color='0044FF')))
				else:
					#if len(dirname)>30:
					#	dirname='..'+dirname[-28:]
					selectlist.append((item[0],colorize_label('移动到【'+item[1]+'】',color='00FF44')))
			for item in dirinfo['subdirs']:
				selectlist.append((item[0],item[1]))
			selectlist.append((-2,colorize_label('新建文件夹',color='CCCC00')))
			sel = dialog.select('源目标：'+title, [q[1] for q in selectlist])
			if sel==-1: return -1
			if cid == selectlist[sel][0]:
				return selectlist[sel][0]
			else:
				if selectlist[sel][0]==-2:
					cid = createdir(cid,title)
				else:
					cid = selectlist[sel][0]
		else:
			cid=0

@plugin.route('/move/<fid>/<filename>')
def move(fid,filename):
	if not ids.raw_dict().has_key('movepid'):
		ids['movepid']=0
	if int(ids['movepid'])<0:
		ids['movepid']=0
	
	pid=getdir(ids['movepid'],filename)
	if str(pid)!='-1':
		data = urllib.urlencode({'fid': fid,'pid':pid})
		try:
			data=xl.urlopen('http://web.api.115.com/files/move',data=data)
			data= xl.fetch(data).replace('\n','').replace('\r','')
			data=json.loads(data[data.index('{'):])
			if data['state']:
				xbmc.executebuiltin('Container.Refresh()')
			else:
				plugin.notify(msg='移动失败,错误信息:'+str(data['error']))
				return
		except:
				plugin.notify(msg='移动失败')
				return
		ids['movepid']=pid

def getfilelistdata(cid,offset,star,typefilter='0',searchstr='0',nf='0'):
	sorttype ='user_ptime'
	if cursorttype['s']=='2' or cursorttype['s']=='3':
		sorttype ='file_size'
	if cursorttype['s']=='4' or cursorttype['s']=='5':
		sorttype ='file_name'
	sortasc='0'
	if cursorttype['s']=='1' or cursorttype['s']=='2' or cursorttype['s']=='4':
		sortasc='1'
	#plugin.notify('%s  %s'%(sorttype,sortasc))
	pageitems = {'0': '25','1': '50','2': '100'}
	pageitem=pageitems[plugin.get_setting('pageitem')]
	return xl.getfilelist(cid,offset,pageitem,star,sorttype,sortasc,typefilter,nf=nf,search_value=searchstr)
	
@plugin.route('/getfilelist/<cid>/<offset>/<star>/<typefilter>/<searchstr>/<changesort>')
def getfilelist(cid,offset,star,typefilter='0',searchstr='0',changesort='0'):
	subcache.clear()
	sorttypelist=['从新到旧','从旧到新','从小到大','从大到小','从A到Z','从Z到A']
	
	if changesort=='1':
		dialog = xbmcgui.Dialog()
		cursorttype['s']=str(dialog.select('文件排序',sorttypelist))
		if cursorttype['s']=='-1':
			return None
	
	typefilter=str(typefilter)
	if typefilter=='-1':
		dialog = xbmcgui.Dialog()
		typefilter=dialog.select('类型筛选',['全部','视频','图片','音乐'])
		typefilter=str(typefilter)
		if typefilter=='-1':
			return None
		if typefilter=='1': typefilter='4'
	
	data=getfilelistdata(cid,offset,star,typefilter,searchstr)

	if data['state']:
		'''
		cookies=''
		cookiedict={}
		plugin.log.error([q[1] for q in xl.cookiejar._cookies['.115.com']['/'].items()])
		for k,v in xl.cookiejar._cookies:
			cookiedict[str(k)]=str(v.value)
		cookiestr=json.dumps(cookiedict)
		cookiestrfile = xbmc.translatePath(os.path.join(__cwd__, 'cookie.txt'))
		with open(cookiestrfile, "wb") as cookietxtFile:
			cookietxtFile.write(cookiestr)
			cookietxtFile.close()
		'''
		#playlistvideo = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
		#playlistvideo.clear()
		
		imagecount=0
		items=[]
		
		itemname='root'
		milkname='115'
		if cid!='0':
			items.append({'label': colorize_label('返回到【%s】'%colorize_label('root', 'dir'),'back'), 'path': plugin.url_for('getfilelist',cid=0,	offset=0,star='0',typefilter=0,searchstr='0',changesort='0')})
		if data.has_key('path'):
			for item in data['path']:
				if item['cid']!=0 and item['cid']!=cid:
					items.append({'label': colorize_label('返回到【%s】'%colorize_label(item['name'], 'dir'),'back'), 'path': plugin.url_for('getfilelist',cid=item['cid'],offset=0,star='0',typefilter=0,searchstr='0',changesort='0')})
				elif item['cid']==cid:
					itemname=item['name']
					milkname=itemname
		if data.has_key('folder'):
			#if data['folder'].has_key('pid'):
			#	items.append({'label': colorize_label('返回到【%s】'%colorize_label(data['folder']['pid'], 'dir'),'back'), 'path': plugin.url_for('getfilelist',cid=data['folder']['pid'],offset=0,star='0',typefilter=0,searchstr='0',changesort='0')})
			if data['folder'].has_key('name'):
				itemname=data['folder']['name']
				milkname=itemname
		if searchstr!='' and searchstr!='0':
			milkname=milkname+'_'+searchstr
		if star=='1':
			milkname=milkname+'_star'
		milkname=milkname[-20:].encode('utf-8').replace('\n','').replace('\r','')
		if str(plugin.get_setting('genm3u8'))=='true':
			items.append({'label': '生成M3U8文件', 'path': plugin.url_for('m3u8',cid=cid,offset=offset,star=star,typefilter=typefilter,searchstr=searchstr,name=milkname)})
		if str(plugin.get_setting('milkvr'))=='true':
			items.append({'label': '生成MilkVR文件', 'path': plugin.url_for('milkvr',cid=cid,offset=offset,star=star,typefilter=typefilter,searchstr=searchstr,name=milkname)})
		#plugin.notify('{"cid":"%s"}'%(cid))
		if searchstr=='' or searchstr=='0':
			items.append({'label': '搜索当前目录【%s】'%colorize_label(itemname, 'dir'),
						'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'disksearch.png') ), 
						'path': plugin.url_for('searchinit',stypes='pan',sstr='0',modify='0',otherargs='{"cid":"%s"}'%(cid))})
			stardisp=colorize_label('★星标过滤-'+('已启用' if star=='1' else '已禁用'), 'star'+str(star))
			items.append({'label': stardisp,'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'star.png') ), 'path': plugin.url_for('getfilelist',cid=cid,offset=0,star='1' if star=='0' else '0',typefilter=typefilter,searchstr=searchstr,changesort='0')})
			
			sorttypedisp=colorize_label('文件排序:'+sorttypelist[int(cursorttype['s'])], 'sort')
			items.append({'label': sorttypedisp, 'path': plugin.url_for('getfilelist',cid=cid,offset=0,star=star,typefilter=typefilter,searchstr=searchstr,changesort='1')})
		else:
			items.append({'label': '返回当前目录【%s】'%colorize_label(itemname, 'dir'),
						'path': plugin.url_for('getfilelist',cid=cid,offset=0,star='0',typefilter=typefilter,searchstr='0',changesort='0')})
		typedisp=colorize_label('筛选:全部', 'filter')
		if typefilter=='4':typedisp=colorize_label('筛选:视频', 'filter')
		if typefilter=='2':typedisp=colorize_label('筛选:图片', 'filter')
		if typefilter=='3':typedisp=colorize_label('筛选:音乐', 'filter')
		items.append({'label': typedisp, 'path': plugin.url_for('getfilelist',cid=cid,offset=0,
		star=star,typefilter='-1',searchstr=searchstr,changesort='0')})
		if data.has_key('data'):
			for item in data['data']:
				#data['data']有时不是list,而是dict, foreach后返回的是key文本。20180425
				if not isinstance(item, dict):
					item=data['data'][item]
				listitem=getListItem(item,itemname)
				if listitem!=None:
					#if listitem.playable:
						#playlistvideo.add(listitem.get_path(), listitem.as_xbmc_listitem())
					items.append(listitem)
					if item.has_key('ms'):
						imagecount+=1
		pageitems = {'0': '25','1': '50','2': '100'}
		pageitem=pageitems[plugin.get_setting('pageitem')]
		if data['count']>int(offset)+int(pageitem):
			items.append({'label': colorize_label('下一页', 'next'),
				'path': plugin.url_for('getfilelist',cid=cid,offset=str(int(offset)+int(pageitem)),
										star=star,typefilter=typefilter,searchstr=searchstr,changesort='0'),
				'thumbnail':xbmc.translatePath( os.path.join( IMAGES_PATH, 'nextpage.png') ).decode('utf-8')})
			#urlcache[cid+"/"+offset+"/"+str(star)] = items
		#xbmc.executebuiltin('Container.SetViewMode(8)')
		#skindir=xbmc.getSkinDir()
		if imagecount >= 10 and imagecount * 2 > len(items):
			setthumbnail['set']=True
			#plugin.notify('setthumbnail')
			#if ALL_VIEW_CODES['thumbnail'].has_key(skindir):
			#	plugin.set_view_mode(ALL_VIEW_CODES['thumbnail'][skindir])
		return items
	else:
		plugin.notify(msg='数据获取失败,错误信息:'+str(data['error']))
		login()
		return

def getimgurl(pc):
	data=xl.urlopen('http://web.api.115.com/files/image?pickcode='+pc+'&_='+str(long(time.time())))		
	data=json.loads(xl.fetch(data))
	imageurl=''
	if data['state']:
		imageurl=data['data']['source_url']
	return imageurl

@plugin.route('/playimg/<pc>/<name>')
def playimg(pc,name):
	imgurl=xl.getfiledownloadurl(pc,changeserver='',withcookie=True)
	xbmc.executebuiltin("ShowPicture(%s)" % (imgurl))
	return
	
def renavitoext():
	for k,v in renameext.items():
		xl.rename(k,v)
	renameext.clear()

def renexttoavi(data):
	exts=['.mp4','.mkv','.iso']
	if data['state']:
		if data.has_key('file_name'):
			if exts.count(data['file_name'][-4:].lower())>0:
				xl.rename(data['file_id'],data['file_name']+'.avi')
				time.sleep(2)
				renameext[data['file_id']]=data['file_name']

def getstm(data,iso,stm):
	if iso=='1':
		return '99'
	
	if stm=='7':
		return '99'
	if stm=='6':
		return '15000000'
	if stm=='5':
		return '7500000'
	if stm=='4':
		return '3000000'
	if stm=='3':
		return '1800000'
	if stm=='2':
		return '1200000'
	if stm=='1':
		return '800000'
	
	if stm=='0' or stm=='-99':
		qtyps=[]
		if data['state']:
			if data.has_key('definition_list'):
				if data['definition_list'].has_key('800000'):
					qtyps.append(('标清','800000'))
				if data['definition_list'].has_key('1200000'):
					qtyps.append(('高清','1200000'))
				if data['definition_list'].has_key('1800000'):
					qtyps.append(('超清','1800000'))
				if data['definition_list'].has_key('3000000'):
					qtyps.append(('1080p','3000000'))
				if data['definition_list'].has_key('7500000'):
					qtyps.append(('4K','7500000'))
				if data['definition_list'].has_key('15000000'):
					qtyps.append(('原画','15000000'))
		if len(qtyps)<=0:
			if stm=='-99':
				return '-1'
			else:
				return '99'
		dialog = xbmcgui.Dialog()
		if stm=='0':
			qtyps.append(( colorize_label('原码','star1'),'99'))
		sel = dialog.select('清晰度', [q[0] for q in qtyps])
		if sel is -1: return '-1'
		stm=str(qtyps[sel][1])
	return stm

def getchangeserver():
	#modify 2018-04-04
	#return 'cdnfhnfile.115.com'
	return '0'
	dialog = xbmcgui.Dialog()
	changeserver=''
	servers = [['cdntel.115.com','vipcdntel.115.com','mzvipcdntel.115.com','fscdntel.115.com','mzcdntel.115.com'],
				['cdnuni.115.com','vipcdnuni.115.com','mzvipcdnuni.115.com','fscdnuni.115.com','mzcdnuni.115.com'],
				['cdngwbn.115.com','vipcdngwbn.115.com','mzvipcdngwbn.115.com','mzcdngwbn.115.com','cdnogwbn.115.com'],
				['cdnctt.115.com','vipcdnctt.115.com','mzvipcdnctt.115.com']]
	
	
	serverchange=int(plugin.get_setting('serverchange'))
	if serverchange>=1 and serverchange<=5:
		selectservers=[]
		if serverchange==1:
			selectservers=sum(servers,[])
		else:
			selectservers=servers[serverchange-2]
		selectservers.insert(0,'不替换')
		sel = dialog.select('CDN替换',selectservers)
		if sel<0:changeserver='-1'
		if sel>0:changeserver=selectservers[sel]
	if serverchange>=6:
		selectservers=sum(servers,[])
		changeserver = selectservers[serverchange-6]
	return changeserver
	
def getvideourl(pc,fid,stm,name=''):
	videourl=''
	if stm=='99':
		changeserver=getchangeserver()
		if changeserver=='-1':
			return '-1'
		#if changeserver!='':
		#	plugin.notify('CDN服务器:'+changeserver)
		playmode=str(plugin.get_setting('playmode'))
		videourl=xl.getfiledownloadurl(pc,changeserver=changeserver,withcookie=True)
		match = re.search("//(?P<CDN>.*115\x2ecom)/", videourl, re.IGNORECASE | re.DOTALL)
		if match:
			#pass
			plugin.notify('CDN服务器:'+ match.group("CDN"))
		if playmode=='0' and videourl:
			#preurl=pre_file_play(fid)
			#result=_http(preurl)
			videourl=get_file_download_url(pc,fid,isvideo=True,changeserver=changeserver,name=urllib.quote_plus(name))
			#plugin.notify('Name:'+ name)
			#videourl=get_file_download_url(pc,fid,isvideo=True,changeserver='cdamz.115.com',name=name)
		#videourl=videourl+'|User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'
	else:
		datam=xl.urlopen('http://115.com/api/video/m3u8/'+pc+'.m3u8')
		datam=xl.fetch(datam)
		m3u8urls=[]
		for match in re.finditer("BANDWIDTH=(?P<bandwidth>.*?)\x2C.*?(?P<url>http.*?)\r", datam, re.IGNORECASE | re.DOTALL):
			m3u8urls.append((int(match.group('bandwidth')),match.group('url')))
		m3u8urls.sort(key=lambda x:x[0],reverse=True)
		for url in m3u8urls:
			if url[0]<=int(stm):
				videourl= url[1]
				break
	return videourl

def getfiledata(pc):
	data=xl.urlopen('http://web.api.115.com/files/video?pickcode='+pc+'&_='+str(long(time.time())))
	data= xl.fetch(data).replace('\n','').replace('\r','')
	data=json.loads(data[data.index('{'):])
	if not data['state']:
		data=xl.urlopen('https://webapi.115.com/files/download?pickcode='+pc+'&_='+str(long(time.time())))
		data= xl.fetch(data).replace('\n','').replace('\r','')
		data=json.loads(data[data.index('{'):])
	return data
	
@plugin.route('/play/<pc>/<name>/<iso>')
def play(pc,name,iso):
	data=getfiledata(pc)
	stm=str(plugin.get_setting('resolution'))
	stm=getstm(data,iso,stm)
	if stm=='-1':
		return
	videourl=''
	if int(stm)>0:
		videourl=getvideourl(pc,data['file_id'],stm,name)
	
	if videourl=='':
		plugin.notify(msg='无视频文件.')
		return
	if videourl=='-1':
		return
		
	sub_pcs={}
	if data['state']:
		if data.has_key('subtitle_info') and str(stm)!='99':
			for s in data['subtitle_info']:
				sub_pcs[('_内置_'+s['title']).decode('utf-8')]=s['url']
	subpath=''
	name=name[:name.rfind('.')].lower()
	for k,v in subcache.items():
		if k.lower().find(name)!= -1:
			#plugin.notify(k)
			#sub_pcs['_same_'+k]=get_file_download_url(v,'')
			sub_pcs['_same_'+k]=xl.getfiledownloadurl(v,changeserver='',withcookie=True)
	
	if plugin.get_setting('subtitle')=='true':
		try:
			uid = xl.getcookieatt('.115.com', 'UID')
			uid = uid[:uid.index('_')]
			data=xl.urlopen('http://web.api.115.com/movies/subtitle?pickcode='+pc)
			data=json.loads(xl.fetch(data))
			if data['state']:
				for s in data['data']:
					sub_pcs[(s['language']+'_'+s['filename']).decode('utf-8')]=s['url']
		except:
			pass
				
	if len(sub_pcs)==1:
		subpath = os.path.join( __subpath__,sub_pcs.keys()[0].decode('utf-8'))
		suburl=sub_pcs[sub_pcs.keys()[0]]
		plugin.notify('加载了1个字幕')
		
	elif len(sub_pcs)>1:
		dialog = xbmcgui.Dialog()
		sel = dialog.select('字幕选择', [subname for subname in sub_pcs.keys()])
		if sel>-1: 
			subpath = os.path.join( __subpath__,sub_pcs.keys()[sel])
			suburl = sub_pcs[sub_pcs.keys()[sel]]
	
	if subpath!='':
		if suburl!='':
			socket = xl.urlopen(suburl)
			subdata = xl.fetch(socket)
			with open(subpath, "wb") as subFile:
				subFile.write(subdata)
			subFile.close()
	'''
	if subpath:
		osWin = xbmc.getCondVisibility('system.platform.windows')
		if osWin:
			playmode=str(plugin.get_setting('playmode'))
			if playmode=='1':
				xbmc.executebuiltin("System.Exec("+__subpath__+")")
	'''
	
	plugin.set_resolved_url(videourl,subpath)
	'''
	player = xbmc.Player()
	player.setSubtitles(subpath)
	for _ in xrange(30):
		if player.isPlaying():
			break
		time.sleep(1)
	else:
		raise Exception('No video playing. Aborted after 30 seconds.')
	'''


@plugin.route('/ffmpeg/<pc>/<name>')
def ffmpeg(pc,name):
	data=getfiledata(pc)
	stm=getstm(data,'0','0')
	videourl=''
	if int(stm)>0:
		videourl=getvideourl(pc,data['file_id'],stm,name)
	if videourl=='':
		plugin.notify(msg='无视频文件.')
		return
	if videourl=='-1':
		return
	plugin.log.error(videourl)
	#videourl=urllib.quote_plus(videourl)
	ext='.mp4'
	#if str(stm)=='99':
		#ext=name[name.rfind('.'):].lower()
	name=name[:name.rfind('.')].lower()
	
	sub_pcs={}
	if data['state']:
		if data.has_key('subtitle_info') and str(stm)!='99':
			for s in data['subtitle_info']:
				sub_pcs[('_内置_'+s['title']).decode('utf-8')]=s['url']
	
	for k,v in subcache.items():
		if k.lower().find(name)!= -1:
			#plugin.notify(k)
			#sub_pcs['_same_'+k]=get_file_download_url(v,'')
			sub_pcs['_same_'+k]=xl.getfiledownloadurl(v,changeserver='',withcookie=True)
	
	if plugin.get_setting('subtitle')=='true':
		try:
			uid = xl.getcookieatt('.115.com', 'UID')
			uid = uid[:uid.index('_')]
			data=xl.urlopen('http://web.api.115.com/movies/subtitle?pickcode='+pc)
			data=json.loads(xl.fetch(data))
			if data['state']:
				for s in data['data']:
					sub_pcs[(s['language']+'_'+s['filename']).decode('utf-8')]=s['url']
		except:
			pass
			
	ffmpegdowloadpath=xbmc.translatePath('/sdcard/Download/115/ffmpegdowload/').decode("utf-8")
	if not os.path.exists(ffmpegdowloadpath):
		os.makedirs(ffmpegdowloadpath)
	suburl=''
	subpath=''
	if len(sub_pcs)==1:
		subpath = os.path.join( ffmpegdowloadpath,sub_pcs.keys()[0])
		suburl=sub_pcs[sub_pcs.keys()[0]]
		plugin.notify('发现1个字幕')
		
	elif len(sub_pcs)>1:
		dialog = xbmcgui.Dialog()
		sel = dialog.select('字幕选择', [subname for subname in sub_pcs.keys()])
		if sel>-1: 
			subpath = os.path.join( ffmpegdowloadpath,sub_pcs.keys()[sel])
			suburl = sub_pcs[sub_pcs.keys()[sel]]
			
	if subpath!='':
		if suburl!='':
			socket = xl.urlopen(suburl)
			subdata = xl.fetch(socket)
			with open(subpath, "wb") as subFile:
				subFile.write(subdata)
			subFile.close()
			subpath=os.path.abspath(subpath)
	
	outputfname=os.path.abspath(xbmc.translatePath(os.path.join(ffmpegdowloadpath, name+ext)).decode("utf-8"))
	batfname=xbmc.translatePath( os.path.join(ffmpegdowloadpath, name+'.bat') ).decode("utf-8")
	with open(batfname, "wb") as batFile:
		batFile.write(ffmpegdl(videourl,outputfname,subpath,stm).encode('gbk'))
		
	batFile.close()
	#plugin.notify("已在/Download/115/ffmpegdowload/目录下生成bat文件")
	plugin.notify(batfname)
	
@plugin.route('/offline_bt/<sha1>')
def offline_bt(sha1):
	dialog = xbmcgui.Dialog()
	ret = dialog.yesno('115网盘提示', '是否离线文件?')
	if ret:
		uid = xl.getcookieatt('.115.com', 'UID')
		uid = uid[:uid.index('_')]
		data=xl.urlopen('http://115.com/?ct=offline&ac=space&_='+str(long(time.time())))
		data=json.loads(xl.fetch(data))
		sign=data['sign']
		_time=data['time']
		data = urllib.urlencode({'sha1': sha1,'uid':uid,'sign':sign,'time':_time})
		data=xl.urlopen('http://115.com/web/lixian/?ct=lixian&ac=torrent',data=data)
		data=json.loads(xl.fetch(data))
		if data['state']:
			wanted='0'
			for i in range(1,len(data['torrent_filelist_web'])):
				wanted+='%02C'
				wanted+=str(i)
			torrent_name=data['torrent_name']
			info_hash=data['info_hash']
			data = urllib.urlencode({'info_hash': info_hash,'wanted': wanted,'savepath': torrent_name,'uid':uid,'sign':sign,'time':_time})
			
			data=xl.urlopen('http://115.com/web/lixian/?ct=lixian&ac=add_task_bt',data=data)
			data=json.loads(xl.fetch(data))
			if data['state']:
				plugin.notify('离线任务添加成功！', delay=2000)
			else:
				plugin.notify(data['error_msg'], delay=2000)
				if data['errcode']==911:
					captcha()
				return
		else:
			plugin.notify(data['error_msg'], delay=2000)
			return
	else:
		return

def pre_file_play(fid):
	return 'http://%s/pre/%s/%s' % (plugin.get_setting('proxyserver'),fid,xl.getcookiesstr())
		
def get_file_download_url(pc,fid,isvideo=False,changeserver='',name=''):
	if isvideo:
		result='http://%s/115/%s/%s/%s/%s' % (plugin.get_setting('proxyserver'),fid,xl.getcookiesstr(),changeserver,name)
	else:
		result=xl.getfiledownloadurl(pc,changeserver,withcookie=True)
	return result

@plugin.route('/delete_offline_list/<hashinfo>/<warringmsg>')
def delete_offline_list(hashinfo,warringmsg):
	dialog = xbmcgui.Dialog()
	ret = dialog.yesno('离线任务删除', warringmsg)
	if ret:
		data=xl.urlopen("http://115.com/web/lixian/?ct=lixian&ac=task_del",data=hashinfo)
		data=xl.fetch(data)
		data=json.loads(data[data.index('{'):])
		
		if data['state']:
			xbmc.executebuiltin('Container.Refresh()')
		else:
			plugin.notify(msg='删除失败,错误信息:'+str(data['error']))
			return

@plugin.route('/offline_list')
def offline_list():
	msg_st={'-1': '任务失败','0': '任务停止','1': '下载中','2': '下载完成'}
	task=xl.offline_list()
	uid = xl.getcookieatt('.115.com', 'UID')
	uid = uid[:uid.index('_')]
	items=[]
	clearcomplete={'time':str(long(time.time())),'uid':uid}
	clearfaile={'time':str(long(time.time())),'uid':uid}
	i=0
	j=0
	
	for item in task:
		if item['status']==2 and item['move']==1:
			clearcomplete['hash['+str(i)+']']=item['info_hash']
			i+=1
		if item['status']==-1:
			clearfaile['hash['+str(j)+']']=item['info_hash']
			j+=1
		
		listitem=ListItem(label=item['name']+colorize_label("["+msg_st[str(item['status'])]+"]", str(item['status'])), label2=None, icon=None, thumbnail=None, path=plugin.url_for('getfilelist',cid=item['file_id'],offset='0',star='0',typefilter='0',searchstr='0',changesort='0'))
		_hash = urllib.urlencode({'uid':uid,'time':str(long(time.time())),r'hash[0]': item['info_hash']})		
		listitem.add_context_menu_items([('删除离线任务', 'RunPlugin('+plugin.url_for('delete_offline_list',hashinfo=_hash,warringmsg='是否删除任务')+')',)],False)
		
		items.append(listitem)
	if j>0:
		_hash = urllib.urlencode(clearfaile)
		items.insert(0, {
			'label': colorize_label('清空失败任务','-1'),
			'path': plugin.url_for('delete_offline_list',hashinfo=_hash,warringmsg='是否清空'+str(j)+'个失败任务')})
	if i>0:
		_hash = urllib.urlencode(clearcomplete)
		items.insert(0, {
			'label': colorize_label('清空完成任务','2'),
			'path': plugin.url_for('delete_offline_list',hashinfo=_hash,warringmsg='是否清空'+str(i)+'个完成任务')})
	return items

@plugin.route('/shellopen/<pc>/<fname>')
def shellopen(pc,fname):
	changeserver=getchangeserver()
	if changeserver=='-1':
		return
	#url=xl.getfiledownloadurl(pc,changeserver,True)
	data=getfiledata(pc)
	url=getvideourl(pc,data['file_id'],'99',fname)
	
	if url=='':
		plugin.notify(msg='无视频文件.')
		return
	if url=='-1':
		return
	comm.shellopenurl(url,samsung=0)
	
@plugin.route('/samsungvr/<pc>/<fname>/<pathname>')
def samsungvr(pc,fname,pathname):
	changeserver=getchangeserver()
	if changeserver=='-1':
		return
	#url=xl.getfiledownloadurl(pc,changeserver,True)
	data=getfiledata(pc)
	
	url=getvideourl(pc,data['file_id'],'99',fname)
	
	if url=='':
		plugin.notify(msg='无视频文件.')
		return
	if url=='-1':
		return
		
	videotypes=['_2dp', '_3dpv', '_3dph','3dv', '3dh', '180x180_3dv', '180x180_3dh','180x180_squished_3dh', '_v360']
	dialog = xbmcgui.Dialog()
	sel = dialog.select('视频类型', videotypes)
	if sel!=-1:
		videotype=videotypes[sel]
		savepath=xbmc.translatePath( os.path.join('/sdcard/MilkVr/115/',pathname.decode("utf-8")[0:40])).decode("utf-8")
		
		if not os.path.exists(savepath):
			os.makedirs(savepath)
		fname=fname.decode("utf-8")[-40:]+'_'+pathname
		fname=fname.decode("utf-8")[0:60]
		fname=fname.encode("utf-8").replace('\n','').replace('\r','')
		fname = re.sub('[\/:*?"<>|]','-',fname)
		mvrlfname=xbmc.translatePath( os.path.join(savepath, fname+'.mvrl')).decode("utf-8")
		with open(mvrlfname, "wb") as mvrlFile:
			mvrlFile.write('mvrl.version=2\n')
			mvrlFile.write('video.url='+url+'\n')
			mvrlFile.write('video.videoType='+videotype+'\n')
			mvrlFile.write('video.audioType=none\n')
			mvrlFile.write('video.thumbnail=http://pic.pptbz.com/pptpic/201411/2014111612541982.jpg\n')
			mvrlFile.write('video.displayTitle='+fname+'\n')
		mvrlFile.close()
		
		savepath=xbmc.translatePath( os.path.join('/sdcard/STRM/115/',pathname.decode("utf-8")[0:40])).decode("utf-8")
		if not os.path.exists(savepath):
			os.makedirs(savepath)
		fname=fname.decode("utf-8")[-40:]+'_'+pathname
		fname=fname.decode("utf-8")[0:60]
		fname=fname.encode("utf-8").replace('\n','').replace('\r','')
		fname = re.sub('[\/:*?"<>|]','-',fname)
		mvrlfname=xbmc.translatePath( os.path.join(savepath, fname+'.strm')).decode("utf-8")
		with open(mvrlfname, "wb") as mvrlFile:
			mvrlFile.write(url+'\n')
		mvrlFile.close()
		
		comm.shellopenurl('milkvr://sideload/?url=%s&video_type=%s'%(url,videotype),samsung=1)
	
global milkvrcount
@plugin.route('/milkvr/<cid>/<offset>/<star>/<typefilter>/<searchstr>/<name>')
def milkvr(cid,offset,star,typefilter='0',searchstr='0',name='0'):
	stm='99'
	videotypes=['_2dp', '_3dpv', '_3dph','3dv', '3dh', '180x180_3dv', '180x180_3dh','180x180_squished_3dh', '_v360']
	dialog = xbmcgui.Dialog()
	sel = dialog.select('视频类型', videotypes)
	global milkvrcount
	milkvrcount=0
	if sel!=-1:
		basepath='/sdcard/MilkVr/115/'
		savepath=xbmc.translatePath( os.path.join( basepath, name.decode("utf-8")[0:40])).decode("utf-8")
		if not os.path.exists(savepath):
			os.makedirs(savepath)
			
		basepath='/sdcard/STRM/115/'
		savepath=xbmc.translatePath( os.path.join( basepath, name.decode("utf-8")[0:40])).decode("utf-8")
		if not os.path.exists(savepath):
			os.makedirs(savepath)
			
		changeserver=getchangeserver()
		if changeserver=='-1':
			return
		htmlfname=xbmc.translatePath( os.path.join(basepath, urllib.quote_plus(name)[0:20]+'.html')).decode("utf-8")
		with open(htmlfname, "wb") as htmlFile:
			htmlFile.write('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8"><TITLE>%s</TITLE><h3>%s</h3>'%(name,name))
			htmlFile.write('\r\n')
		htmlFile.close()
		genmvrl(cid,offset,star,typefilter,searchstr,videotypes[sel],stm,changeserver,name)
	plugin.notify(msg='生成'+str(milkvrcount)+'个MVRL文件！')

def genmvrl(cid,offset,star,typefilter,searchstr,videotype,stm,changeserver='',name=''):
	global milkvrcount
	if milkvrcount>=200:
		return
	#if star=='1':
	data=getfilelistdata(cid,offset,star,typefilter,searchstr)
	if data['state']:
		pname=''
		if data.has_key('path'):
			pname=data['path'][len(data['path'])-1]['name'];
		if data.has_key('folder'):
			if data['folder'].has_key('name'):
				pname=data['folder']['name']
		
		for item in data['data']:
			if item.has_key('sha'):
				if (item.has_key('iv') or item['ico'] in videoexts) and int(item['s'])>120000000:
					url=getvideourl(item['pc'],item['fid'],stm,item['n'].encode('UTF-8'))
					if url!='':
						fname=item['n']
						fname=fname[:fname.rfind('.')]
						if len(fname)<=20:
							if item.has_key('dp'):
								fname=fname+'_'+item['dp'];
							else:
								fname=fname+'_'+pname
						#fname=fname.decode("utf-8")[-40:]+'_'+pname
						fname=fname.decode("utf-8")[0:30]+fname.decode("utf-8")[-20:]
						fname=fname.encode("utf-8").replace('\n','').replace('\r','')
						fname = re.sub('[\/:*?"<>|]','-',fname)
						
						basepath='/sdcard/MilkVr/115/'
						savepath=xbmc.translatePath( os.path.join( basepath, name.decode("utf-8")[0:40])).decode("utf-8")
						mvrlfname=xbmc.translatePath( os.path.join(savepath, fname+'.mvrl')).decode("utf-8")
						with open(mvrlfname, "wb") as mvrlFile:
							mvrlFile.write('mvrl.version=2\n')
							mvrlFile.write('video.url='+url+'\n')
							mvrlFile.write('video.videoType='+videotype+'\n')
							mvrlFile.write('video.audioType=none\n')
							mvrlFile.write('video.thumbnail=http://pic.pptbz.com/pptpic/201411/2014111612541982.jpg\n')
							mvrlFile.write('video.displayTitle='+fname+'\n')
						mvrlFile.close()
						htmlfname=xbmc.translatePath( os.path.join('/sdcard/MilkVr/115/', name+'.html') ).decode("utf-8")
						with open(htmlfname, "ab") as htmlFile:
							htmlFile.write('<DT><a href="milkvr://sideload/?url=%s&video_type=%s" type="video/mp4" >%s</a>'%(url,videotype,fname))
						htmlFile.close()
						
						basepath='/sdcard/STRM/115/'
						savepath=xbmc.translatePath( os.path.join( basepath, name.decode("utf-8")[0:40])).decode("utf-8")
						mvrlfname=xbmc.translatePath( os.path.join(savepath, fname+'.strm')).decode("utf-8")
						with open(mvrlfname, "wb") as mvrlFile:
							mvrlFile.write(url+'\n')
						mvrlFile.close()
						
						
					milkvrcount+=1
					if milkvrcount>=200:
						break
			else:
				genmvrl(item['cid'],'0','0','0','0',videotype,stm,changeserver,name)

@plugin.route('/m3u8/<cid>/<offset>/<star>/<typefilter>/<searchstr>/<name>')
def m3u8(cid,offset,star,typefilter='0',searchstr='0',name='0'):
	stm='0'
	qtyps=[]		
	qtyps.append(('标清','800000'))
	qtyps.append(('高清','1200000'))
	qtyps.append(('超清','1800000'))
	qtyps.append(('1080p','3000000'))
	qtyps.append(('4K','7500000'))
	qtyps.append(('原画','15000000'))
	dialog = xbmcgui.Dialog()
	sel = dialog.select('清晰度', [q[0] for q in qtyps])
	if sel is -1: return '-1'
	stm=str(qtyps[sel][1])

	global milkvrcount
	milkvrcount=0

	basepath='/sdcard/Download/115/'
	savepath=xbmc.translatePath( os.path.join( basepath, name)).decode("utf-8")[0:40]
	if not os.path.exists(savepath):
		os.makedirs(savepath)
	htmlfname=xbmc.translatePath( os.path.join(basepath, name[0:20]+'.html') ).decode("utf-8")
	with open(htmlfname, "wb") as htmlFile:
		htmlFile.write('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8"><TITLE>%s</TITLE><h3>%s</h3>'%(name,name))
		htmlFile.write('\r\n')
	htmlFile.close()
	genm3u8(cid,offset,star,typefilter,searchstr,savepath,stm,name)
	
	plugin.notify(msg='在/Download/115/目录下生成'+str(milkvrcount)+'个M3U8文件！')
	
def ffmpegdl(input,output,subtitle='',stm='-1'):
	#ffmpegopt='-err_detect ignore_err -filter:v pad=11/10*iw:ih:(ow-iw)/2:0,stereo3d=sbsl:abl,crop=10/11*iw:ih:(iw-ow)/2:0,stereo3d=abl:sbsl -y -bsf:a aac_adtstoasc'
	ffmpegopt='-c copy -y -bsf:a aac_adtstoasc'
	if stm=='99':
		ffmpegopt='-c copy -y'
	dlcmd=''
	times1=''
	times2=''
	timedt=''
	
	dialog=xbmcgui.Dialog()
	ret = dialog.yesno('115网盘提示', '是否剪切片断?')
	
	if ret:
		times=keyboard(text='00:00:00',title='起始时间')
		if times:
			timee=keyboard(text=times,title='结束时间')
			if timee:
				times=time.strptime(times,'%H:%M:%S')
				times=timedelta(hours=times.tm_hour,minutes=times.tm_min,seconds=times.tm_sec)
				timee=time.strptime(timee,'%H:%M:%S')
				timee=timedelta(hours=timee.tm_hour,minutes=timee.tm_min,seconds=timee.tm_sec)
				tdelta=timee-times
				tdelta=tdelta.total_seconds()
				if tdelta>0:
					timedt=' -t '+str(tdelta)+' '
					timefs=timedelta(hours=0,minutes=0,seconds=30)
					if times>timefs:
						times1='-ss '+str(times-timefs)
						times2='-ss 00:00:30'
					else:
						times1=''
						times2='-ss '+str(times)
	
	subtitlecs=''
	subtitlets=''
	if subtitle!='':
		subtitle='-i "'+subtitle+'"'
		subtitlecs='-c:s mov_text'
		subtitlets=times1
	dlcmd='ffmpeg %s -i \"%s\" %s %s %s %s %s %s \"%s\"'%(times1,input,subtitlets,subtitle,ffmpegopt,subtitlecs,times2,timedt,output)
	#dlcmd= u'ffmpeg %s -i \"%s\" %s %s %s %s %s \"%s\"'%(times1,input,subtitle,ffmpegopt,subtitlecs,times2,timedt,output)
	
		
	#ffmpegopt='-err_detect ignore_err -filter:v pad=11/10*iw:ih:(ow-iw)/2:0,stereo3d=sbsl:abl,crop=10/11*iw:ih:(iw-ow)/2:0,stereo3d=abl:sbsl -y -bsf:a aac_adtstoasc'
	#dlcmd=dlcmd+'\r\n'+'ffmpeg -i "'+output+'" '+ffmpegopt+' "'+output+'.mp4"'
	return dlcmd
	
def genm3u8(cid,offset,star,typefilter,searchstr,savepath,stm,name):
	global milkvrcount
	if milkvrcount>=200:
		return
	data=getfilelistdata(cid,offset,star,typefilter,searchstr)
	if data['state']:
		pname=''
		if data.has_key('path'):
			pname=data['path'][len(data['path'])-1]['name'];
		if data.has_key('folder'):
			if data['folder'].has_key('name'):
				pname=data['folder']['name']
		pname=pname
		for item in data['data']:
			if item.has_key('sha'):
				if item.has_key('iv'):
					fname=item['n']
					fname=fname[:fname.rfind('.')]
					if len(fname)<=20:
						if item.has_key('dp'):
							fname=fname+'_'+item['dp']
						else:
							fname=fname+'_'+pname
					fname=fname.decode("utf-8")[-40:]+'_'+pname
					fname=fname.decode("utf-8")[0:60]
					fname=fname.encode("utf-8").replace('\n','').replace('\r','')
					fname = re.sub('[\/:*?"<>|]','-',fname)
					#plugin.log.error(fname)
					url=getvideourl(item['pc'],item['fid'],stm)
					if url!='':
						m3u8fname=xbmc.translatePath(os.path.join(savepath, fname+'.m3u8')).decode("utf-8")
						#plugin.notify(m3u8fname)
						with open(m3u8fname, "wb") as m3u8File:
							
							m3u8File.write('#EXTM3U\r\n#EXT-X-STREAM-INF:PROGRAM-ID=1,NAME="%s"\r\n'%(fname))
							m3u8File.write(url)
							'''
							data=xl.urlopen(url)
							data= xl.fetch(data)
							matchkeyurl=re.search(r'(?P<keyurl>\x2Fapi\x2Fvideo\x2Fm3u8\x2Fvideo\x2ekey.*?)[\x22\x27]', data, re.DOTALL | re.IGNORECASE)
							if matchkeyurl:
								keyurl=matchkeyurl.group('keyurl')
								keyurl2=urlparse.urljoin(url, keyurl)
								data=data.replace(keyurl,keyurl2)
							m3u8File.write(data)
							'''
						m3u8File.close()
						
						ffmpegdowloadpath=xbmc.translatePath('/sdcard/Download/115/ffmpegdowload/').decode("utf-8")
						if not os.path.exists(ffmpegdowloadpath):
							os.makedirs(ffmpegdowloadpath)
						outputfname=xbmc.translatePath(os.path.join(ffmpegdowloadpath, fname+'.mp4')).decode("utf-8")
						batfname=xbmc.translatePath( os.path.join(ffmpegdowloadpath, fname+'.bat') ).decode("utf-8")
						with open(batfname, "wb") as batFile:
							batFile.write(ffmpegdl(url,os.path.abspath(outputfname).decode("utf-8")))
							batFile.write('\r\n')
						batFile.close()
						'''
						h5playpath=xbmc.translatePath('/sdcard/Download/115/html/').decode("utf-8")
						if not os.path.exists(h5playpath):
							os.makedirs(h5playpath)
						h5playfname=xbmc.translatePath(os.path.join(h5playpath, fname+'.html')).decode("utf-8")
						with open(h5playfname, "wb") as h5playFile:
							h5playFile.write('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8"><TITLE>%s</TITLE><h3>%s</h3><DT><video width="640" height="480" autoplay="autoplay" src="%s" controls="controls" type="application/x-mpegURL">%s</video>'%(fname,fname,'../'+name+'/'+fname+'.m3u8',fname))
						h5playFile.close()
						'''
						if url[-4:]=='m3u8':
							htmlfname=xbmc.translatePath( os.path.join('/sdcard/Download/115/', name+'.html') ).decode("utf-8")
							with open(htmlfname, "ab") as htmlFile:
								#htmlFile.write('<DT><a href="%s" type="video/mp4" >%s</a>\r\n'%(name+'/'+fname+'.m3u8',fname))
								htmlFile.write('<DT><a href="%s" type="video/mp4" >%s</a>'%(url,fname))
								#htmlFile.write('<DT><a href="%s" type="application/x-mpegURL" >%s</a>'%(url,fname))
								#htmlFile.write('<DT><a href="html/%s.html" type="application/x-mpegURL" >%s</a>'%(fname,fname))
								#htmlFile.write('\r\n')
							htmlFile.close()
						
						
					milkvrcount+=1
					if milkvrcount>=200:
						break
			else:
				genm3u8(item['cid'],'0','0','0','0',savepath,stm,name)

@plugin.route('/lxlist/<cid>/<name>')
def lxlist(cid,name):
	dialog = xbmcgui.Dialog()
	ret = dialog.yesno('115网盘提示', '是否包含子文件夹?')
	lists=getlxlist(cid,ret)
	x=0
	#plugin.log.error(lists)
	if len(lists)>0:
		strs=name+'\n'
		for item in lists:
			strs += item['n']+"|115:"+item['pc']+"|"+item['u']+'\n'
			if len(strs)>40000:
				data = urllib.urlencode({'nid': '', 'content': strs, 'cid': '0'})
				data=xl.urlopen("http://115.com/note/?ct=note&ac=save",data=data)
				x=x+1
				strs=name+"-"+str(x)+'\n'
		data = urllib.urlencode({'nid': '', 'content': strs, 'cid': '0'})
		data=xl.urlopen("http://115.com/note/?ct=note&ac=save",data=data)
		data= xl.fetch(data).replace('\n','').replace('\r','')
		data=json.loads(data[data.index('{'):])
		#plugin.log.error(data)
		if data['state']:
			plugin.notify(msg='制作成功！')
		else:
			plugin.notify(msg='制作失败！'+str(data['msg']))

def getlxlist(cid,alls):
	lists=[]
	offsets=0
	if alls:
		while True:
			data=xl.urlopen("http://web.api.115.com/files?aid=1&cid="+cid+"&type=4&star=0&o=user_ptime&asc=0&offset="+str(offsets)+"&show_dir=1&limit=80&format=json")
			data= xl.fetch(data).replace('\n','').replace('\r','')
			data=json.loads(data[data.index('{'):])
			if data['state']:
				for item in data['data']:
					if item.has_key('sha'):
						if item.has_key('iv'):
							lists.append({'n':item['n'],'pc':item['pc'],'u':item['u']})
				if data['count']>data['offset']+80:
					offsets=data['offset']+80
				else:
					break;
			else:
				break;
		return lists
	else:
		while True:
			data=xl.urlopen("http://web.api.115.com/files?aid=1&cid="+cid+"&type=&star=0&o=user_ptime&asc=0&offset="+str(offsets)+"&show_dir=1&limit=80&format=json")
			data= xl.fetch(data).replace('\n','').replace('\r','')
			data=json.loads(data[data.index('{'):])
			if data['state']:
				for item in data['data']:
					if item.has_key('sha'):
						if item.has_key('iv'):
							lists.append({'n':item['n'],'pc':item['pc'],'u':item['u']})
				if data['count']>data['offset']+80:
					offsets=data['offset']+80
				else:
					break;
			else:
				break;
		return lists
		
@plugin.route('/cleartempplay')
def cleartempplay():
	cleartempplayurl='http://%s/115/%s/%s/%s/%s' % (plugin.get_setting('proxyserver'),'cleartempplay',xl.getcookiesstr(),'','')
	xl.urlopen(cleartempplayurl)

@plugin.route('/captcha/')
def captcha():
	captchadlg=CaptchaDlg()
	captchadlg.doModal()
	#qthread = threading.Thread(target=captchadlg.doModal,)
	#qthread.start()
	
@plugin.route('/offline/<url>')
def offline(url):
	xbmc.executebuiltin( "ActivateWindow(busydialog)" )
	data=xl.offline(url)
	#plugin.log.error(data)
	if data['state']:
		plugin.notify(u' 添加离线成功'.encode('utf-8'),delay=1000)
	else:
		if data['errcode']==911:
			plugin.notify(data['error_msg'],delay=2000)
			captcha()
		else:
			magnet = ''
			match = re.search(r'\x3Abtih\x3a(?P<magnet>[0-9a-f]{40})', url, re.IGNORECASE | re.DOTALL)
			if match:
				magnet = match.group('magnet')
			if magnet:
				plugin.notify(u'磁力离线失败,已尝试下载种子文件，请一段时间后查看',delay=1000)
				#torrenturl='https://btdb.eu/tfiles/%s.torrent'%(magnet)
				#offline(torrenturl)
				torrenturl='http://itorrents.org/torrent/%s.torrent'%(magnet)
				offline(torrenturl)
			else:
				plugin.notify(u' 添加离线失败,错误代码:'.encode('utf-8')+data['error_msg'],delay=1000)
		
	xbmc.executebuiltin( "Dialog.Close(busydialog)" )
	if data['state']:
		return data['info_hash']
	else:
		return

@plugin.route('/execmagnet/<url>/<title>/<msg>')
def execmagnet(url,title='',msg=''):
	dialog = xbmcgui.Dialog()
	ret = dialog.yesno('是否离线 '+title+'?', msg)
	if ret:
		info_hash=offline(url)
		
if __name__ == '__main__':
	# Override default handler
	plugin.run()
	skindir=xbmc.getSkinDir()
	if setthumbnail['set']:
		if comm.ALL_VIEW_CODES['thumbnail'].has_key(skindir):
			plugin.set_view_mode(comm.ALL_VIEW_CODES['thumbnail'][skindir])

