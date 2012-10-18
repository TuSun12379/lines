#!/usr/bin/env python2.7-32

import sys

import argparse
import numpy as np

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms

from scipy.interpolate import interp1d

from shutil import copyfile

__version__ = '16-10-2012'


params = {'legend.fontsize': 10,
		  'legend.labelspacing': 0.1}
plt.rcParams.update(params)




def gen_read_files(paths):
	"""opens file, returns file object for reading"""
	for path in paths:
		try:
			f = open(path,'r')
		except IOError:
			print 'cannot open', path
			exit(0)
		yield f

def read_file(path):
	"""opens file, returns file object for reading"""
	try:
		f = open(path,'r')
	except IOError:
		print 'cannot open', path
		exit(0)
	return f


def read_data(f,usecols=None,append_zeros=False):
	inp = np.loadtxt(f,usecols=usecols)

	if inp.ndim == 1:
		(i,) = inp.shape
		inp.shape = (i,-1)

	assert inp.ndim == 2, 'This should not happen...'

	if append_zeros:
		(i,j) = inp.shape


		inp = np.hstack((inp,np.zeros((i,1))))


	if inp.shape[1] > 3:
		print 'More than 3 columns read from {}, assuming x,y,esd, ignoring the rest.'.format(f.name)

	d = Data(inp,name=f.name)

	return d

def load_tick_marks(path):
	"""Checks if file exists and loads tick mark data as data class"""
	try:
		f = open(path,'r')
	except IOError:
		print '-- {} not found. (IOError)'.format(path)
		ticks = None
	else:
		ticks = read_data(f,usecols=(3,),append_zeros=True)
	finally:
		return ticks


def parse_xrs(f,return_as='d_xrs'):
	xy = np.array([],dtype=float).reshape(0,2)
	start = True
	finish = False
	pre = []
	post = []

	x = []
	y = []
	esd = []

	for line in f:
		# print start,finish

		# if 'finish' in line.lower() or 'end' in line.lower():
		# 	finish = True
			
		# 	# Takes care of new xrs files with no bgvalu commands
		# 	start = False
		# 	post.append(line)
		# elif line.lower().startswith('bgvalu') and not finish:
		# 	start = False
		# 	x,y = [float(item) for item in line.split()[1:]]
		# 	xy = np.append(xy,[[x],[y]],axis=1)
		# elif start:
		# 	pre.append(line)
		# elif finish or not start:
		# 	post.append(line)

		if 'finish' in line.lower() or 'end' in line.lower():
			# Takes care of new xrs files with no bgvalu commands
			start = False
			post.append(line)
		elif line.lower().startswith('bgvalu') and start:
			inp = line.split()
			x.append(float(inp[1]))
			y.append(float(inp[2]))
			try:
				esd.append(float(inp[3]))
			except IndexError:
				esd.append(np.nan)
		elif start:
			pre.append(line)
		elif not start:
			post.append(line)

	f.close()

	if return_as == 'xye':
		return np.vstack([x,y,esd]).T
	elif return_as == 'xy':
		return np.vstack([x,y]).T
	elif return_as == 'd':
		xye = np.vstack([x,y,esd]).T
		d = Data(xye,name='stepco.inp')
		return d
	elif return_as == 'd_xrs':
		xye = np.vstack([x,y,esd]).T
		d = Data(xye,name='stepco.inp')
		xrs = [f.name,pre,post]
		return d,xrs
	else:
		raise SyntaxError





def parse_crplot_dat(f):
	"""Parses crplot.dat file"""
		
	# skip first 2 lines
	f.next()
	f.next()

	ret = []

	for line in f:
		inp = line.split()
		if not f:
			continue
		ret.append([float(val) for val in inp])

	return ret

def parse_hkl_dat(f):
	ret = []

	for line in f:
		inp = line.split()
		if not f:
			continue
		ret.append([float(val) for val in inp])

	return ret

def plot_stdin(fig,update_time=0.2):
	import time
	TclError =  matplotlib.backends.backend_tkagg.tkagg.Tk._tkinter.TclError

	print 'Reading stdin.\n'

	def nrange(n=0):
		while True:
			yield n
			n=n+1

	iterator = (n for n in nrange())

	#fig = plt.figure()
	ax = fig.add_subplot(111)

	x = []
	y = []
	
	l1, = ax.plot(x,y,label='stdin')

	plt.legend()
	fig.show()

	t0 = time.time()

	while True:
		try:
			line = sys.stdin.readline()
		except KeyboardInterrupt as e:
			print e
			break
		
		if line == '':
			try:
				fig.canvas.flush_events() # update figure to prevent slow responsiveness
			except TclError:
				print '-- Window closed (TclError on readline).'
				break

			try:
				time.sleep(0.05) # prevent high cpu usage
			except KeyboardInterrupt as e:
				print e
				break
			else:
				continue
		
		inp = line.split()

		try:
			y.append(float(inp[1]))
			x.append(float(inp[0]))
		except IndexError:
			x.append(iterator.next())
			y.append(float(inp[0]))
		
		if time.time() - t0 > update_time:
			# drawing is slow, better to refresh ever x seconds
			
			t0 = time.time()

			l1.set_xdata(x)
			l1.set_ydata(y)
			
			ax.relim()
			ax.autoscale()
			
			plt.draw()
			
			try:
				fig.canvas.flush_events() # update figure to prevent slow responsiveness
			except TclError:
				print '-- Window closed (TclError on update).'
				break


def f_monitor(fn,f_init,f_update,fig=None,poll_time=0.05):
	"""experimental function for live monitoring of plots"""
	import os
	import time

	TclError =  matplotlib.backends.backend_tkagg.tkagg.Tk._tkinter.TclError

	if not fig:
		fig = plt.figure()
	
	ax = fig.add_subplot(111)

	args = f_init(fn,fig,ax)

	plt.legend()
	fig.show()

	current_lastmod = os.stat(fn).st_mtime

	while True:
		if os.stat(fn).st_mtime == current_lastmod:
			# flushing here as well, to prevent locking up of mpl window			
			
			try:
				fig.canvas.flush_events()
			except TclError:
				print '-- Window closed (TclError).'
				break

			# low poll time is needed to keep responsiveness
			
			try:
				time.sleep(poll_time)
			except KeyboardInterrupt as e:
				print e
				break

		else:
			print 'Updated:', time.ctime(os.stat(fn).st_mtime)
			current_lastmod = os.stat(fn).st_mtime

			args = f_update(fn,*args)

			#ax.relim()
			#ax.autoscale()	# resets the boundaries -> annoying for a plot that doesn't need rescaling
			plt.draw()
			
			# And this allows you to at least close the window (and crash the program by that ;))
			fig.canvas.flush_events()
		

def plot_init(fn,fig,ax):
	f = read_file(fn)
	d = read_data(f)
	f.close()

	line, = ax.plot(d.x,d.y,label=fn)

	return [line]


def plot_update(fn,*args):
	[line] = args

	f = read_file(fn)
	d = read_data(f)
	f.close()

	line.set_data(d.x,d.y)

	return [line]


def crplot_init(fn,fig,ax):

	fcr = open('crplot.dat','r')
	fhkl = open('hkl.dat','r')
		
	crdata = np.array(parse_crplot_dat(fcr))
	hkldata = np.array(parse_hkl_dat(fhkl))
	
	fcr.close()
	fhkl.close()

	tt = crdata[:,0]
	obs = crdata[:,1] 
	clc = crdata[:,2]
	dif = crdata[:,3]
	
	tck = hkldata[:,3]
	
	mx_dif = max(dif)
	mx_pat = max(max(obs),max(clc))
	
	pobs, = ax.plot(tt, obs, label = 'observed')
	pclc, = ax.plot(tt, clc, label = 'calculated')
	pdif, = ax.plot(tt, dif - mx_dif, label = 'difference')
	
	pobs_zero, = ax.plot(tt,np.zeros(tt.size), c='black')
	pdif_zero, = ax.plot(tt,np.zeros(tt.size) - mx_dif, c='black')
	
	ptcks, = ax.plot(tck,np.zeros(tck.size) - (mx_dif / 4), linestyle='', marker='|', markersize=10, label = 'ticks', c='purple')
	
	args = [pobs, pclc, pdif, pobs_zero, pdif_zero, ptcks]

	return args


def crplot_update(fn,*args):
	pobs, pclc, pdif, pobs_zero, pdif_zero, ptcks = args

	fcr = open('crplot.dat','r')
	fhkl = open('hkl.dat','r')
	
	crdata = np.array(parse_crplot_dat(fcr))
	hkldata = np.array(parse_hkl_dat(fhkl))
	
	fcr.close()
	fhkl.close()

	tt = crdata[:,0]
	obs = crdata[:,1] 
	clc = crdata[:,2]
	dif = crdata[:,3]
	
	tck = hkldata[:,3]
	
	mx_dif = max(dif)
	mx_pat = max(max(obs),max(clc))

	pobs.set_data(tt,obs)
	pclc.set_data(tt,clc)
	pdif.set_data(tt,dif - mx_dif)
	pobs_zero.set_data(tt,np.zeros(tt.size))
	pdif_zero.set_data(tt,np.zeros(tt.size) - mx_dif)
	ptcks.set_data(tck,np.zeros(tck.size) - (mx_dif / 4))

	args = [pobs, pclc, pdif, pobs_zero, pdif_zero, ptcks]

	return args


def f_crplo():
	## difference data
	crplotdat = 'crplot.dat'
	fcr = open(crplotdat,'r')
	
	crdata = np.array(parse_crplot_dat(fcr))
	
	tt = crdata[:,0]
	obs = crdata[:,1] 
	clc = crdata[:,2]
	dif = crdata[:,3]
	
	mx_dif = max(dif)
	mx_pat = max(max(obs),max(clc))
	
	plt.plot(tt, obs, label = 'observed')
	plt.plot(tt, clc, label = 'calculated')
	plt.plot(tt, dif - mx_dif, label = 'difference')
	
	plt.plot(tt, np.zeros(tt.size), c='black')
	plt.plot(tt, np.zeros(tt.size) - mx_dif, c='black')

	## tick marks
	hkldat = 'hkl.dat'
	try:
		fhkl = open(hkldat,'r')
	except IOError:
		print '-- hkl.dat not found. (IOError)'
	else:
		hkldata = np.array(parse_hkl_dat(fhkl))
		tck = hkldata[:,3]
		plt.plot(tck,np.zeros(tck.size) - (mx_dif / 4), linestyle='', marker='|', markersize=10, label = 'ticks', c='purple')


def f_plot_christian(bg_xy):
	crplotdat = 'crplot.dat'
	try:
		fcr = open(crplotdat,'r')
	except IOError:
		print '\n{} not found. Skipping difference plot.'.format(crplotdat)
	else:
		crdata = np.array(parse_crplot_dat(fcr))
		tt = crdata[:,0]
		dif = crdata[:,3]
	
		bg_interpolate = interpolate(bg_xy,tt,kind='linear')
		
		plt.plot(tt, bg_interpolate + dif, label = 'bg + diff')

def f_bg_correct_out(d,bg_xy):
	fn_bg   = d.filename.replace('.','_bg.')
	fn_corr = d.filename.replace('.','_corr.')
	out_bg   = open(fn_bg,'w')
	out_corr = open(fn_corr,'w')
		
	xvals = d.x
	yvals = d.y
	
	bg_yvals = interpolate(bg_xy,xvals,kind=options.bg_correct)
	offset = raw_input("What offset should I add to the data?\n >> [0] ") or 0
	offset = int(offset)
	if len(bg_xy) >= 4:
		print 'Writing background pattern to %s' % fn_bg
		for x,y in zip(xvals,bg_yvals):
			if np.isnan(y): 
				continue
			print >> out_bg, '%15.6f%15.2f' % (x,y)
		print 'Writing corrected pattern to %s' % fn_corr
		for x,y in zip(xvals,yvals-bg_yvals+offset):
			if np.isnan(y): 
				continue
			print >> out_corr, '%15.6f%15.2f' % (x,y)
	else:
		raise IndexError, 'Not enough values in array bg_xy.'



def new_stepco_inp(xy,name,pre,post,esds=None):
	"""Function for writing stepco input files"""

	print 'Writing xy data to file {}'.format(name)

	f = open(name,'w')

	for line in pre:
		print >> f, line,

	if np.any(esds):
		esds = esds.reshape(1,-1)

		for (x,y,esd) in np.vstack((xy,esds)).T:
			if np.isnan(esd):
				esd = ''
			else:
				esd = '{:15.2f}'.format(esd)
			print >> f, 'BGVALU    {:15f}{:15.2f}{}'.format(x,y,esd)
	else:	
		for x,y in xy.T:
			print >> f, 'BGVALU    {:15f}{:15.2f}'.format(x,y)

	for line in post:
		print >> f, line,

	f.close()



def interpolate(arr,xvals,kind='cubic'):
	"""
	arr is the data set to interpolate
	
	xvals are the values it has to be interpolated to
	
	kind is the type of correction, Valid options: 'linear','nearest','zero', 
	'slinear', 'quadratic, 'cubic') or as an integer specifying the order 
	of the spline interpolator to use.
	"""

	assert arr.ndim == 2, 'Expect a 2-dimentional array'

	try:
		kind = int(kind)
	except ValueError:
		if arr.shape[0] < 4:
			kind = 'linear'
	else:
		if arr.shape[0] < kind+1:
			kind = 'linear'
	
	x = arr[:,0] # create views
	y = arr[:,1] #
	res = interp1d(x,y,kind=kind,bounds_error=False)

	# if the background seems to take shortcuts in linear mode, this is because fixed steps
	# were set in the Backgrounder class

	return res(xvals)




class Data(object):
	total = 0
	"""container class for x,y, err data"""
	def __init__(self,arr,name=None):
		print 'Loading data: {}\n       shape: {}\n'.format(name,arr.shape)

		self.arr = arr
		self.x   = self.arr[:,0]
		self.y   = self.arr[:,1]
		self.xy  = self.arr[:,0:2]
		self.xye = self.arr[:,0:3]

		try:
			self.err = self.arr[:,2]
		except IndexError:
			self.err = None

		if np.all(self.err == np.nan):
			self.has_esd = False
			self.err = None
		else:
			self.has_esd = True

		self.index = self.total
		self.filename = name
		Data.total += 1


class Background():
	sensitivity = 8

	def __init__(self,fig,d=None, outfunc=None,bg_correct=False):
		"""Class that captures mouse events when a graph has been drawn, stores the coordinates
		of these points and draws them as a line on the screen. Can also remove points and print all
		the stored points to stdout

		http://matplotlib.sourceforge.net/users/event_handling.html
		http://matplotlib.sourceforge.net/api/pyplot_api.html#matplotlib.pyplot.plot

		Takes:
		a figure object
		optional numpy array with background coordinates, shape = (2,0)

		xy: 2d ndarray, shape(2,0) with x,y data"""

		self.ax = fig.add_subplot(111)
		
		# if xy is None:
		# 	self.xy = np.array([],dtype=float).reshape(2,0)
		# else:
		# 	idx = xy[0,:].argsort()
		# 	self.xy = xy[:,idx]

		if d:
			self.d  = d
			self.xy = np.array(self.d.xy,copy=True).T
		else:
			self.d  = None
			self.xy = None

		try:
			idx = self.xy[0,:].argsort()
			self.xy = self.xy[:,idx]
		except (IndexError, ValueError, TypeError):
			self.xy = np.array([],dtype=float).reshape(2,0)

		self.line, = self.ax.plot(*self.xy,lw=0.5,marker='s',mec='red',mew=1,mfc='None',markersize=3,picker=self.sensitivity,label='interactive background')

		self.pick  = self.line.figure.canvas.mpl_connect('pick_event', self.onpick)
		self.cid   = self.line.figure.canvas.mpl_connect('button_press_event', self)

		self.keyevent = self.line.figure.canvas.mpl_connect('key_press_event', self.onkeypress)

		self.n = 0

		self.tb = plt.get_current_fig_manager().toolbar

		print
		print 'Left mouse button: add point'
		print 'Right mouse button: remove point'
		print 'Middle mouse button or press "a": print points to file/stdout'
		print
		print 'Note: Adding/Removing points disabled while using drag/zoom functions.'
		print

		self.bg_correct = bg_correct
		if self.bg_correct:
			self.bg_range = np.arange(self.xy[0][0],self.xy[0][1],0.01) # Set limited range to speed up calculations
			self.bg, = self.ax.plot(self.d.x,self.d.y,label='background')
			#print self.bg_range


	def __call__(self,event):
		"""Handles events (mouse input)"""
		# Skips events outside of canvas
		if event.inaxes!=self.line.axes:
			return
		# Skips events if any of the toolbar buttons are active	
		if self.tb.mode!='':
			return
		
		xdata = event.xdata
		ydata = event.ydata
		x,y = event.x, event.y

		button = event.button
		#print event

		if button == 1: #lmb
			self.add_point(x,y,xdata,ydata)
		if button == 2: # mmb
			self.printdata()
		if button == 3: # rmb
			pass

		if self.bg_correct and button:
			self.background_update()
	
		self.line.set_data(self.xy)
		self.line.figure.canvas.draw()


	def onpick(self,event):
		"""General data point picker, should work for all kinds of plots?"""
		if not event.mouseevent.button == 3: # button 3 = right click
			return

		ind = event.ind

		removed = self.xy[:,ind]
		self.xy = np.delete(self.xy,ind,1)

		for n in range(len(ind)):
			print '   --- {} {}'.format(*removed[:,n])


	def onkeypress(self,event):
		if event.key == 'x':
			print 'x pressed'
		if event.key == 'y':
			print 'y pressed'
		if event.key == 'z':
			print 'z pressed'
		if event.key == 'a':
			print '\na pressed'
			self.printdata()
	

	def add_point(self,x,y,xdata,ydata):
		"""Store both data points as relative x,y points. The latter are needed to remove points"""

		print '+++    {} {}'.format(xdata, ydata)

		self.xy = np.append(self.xy,[[xdata],[ydata]],axis=1)
		idx = self.xy[0,:].argsort()
		self.xy = self.xy[:,idx]
	

	def background_update(self):
		xy = self.xy.T

		if xy.shape[0] < 2:
			self.bg.set_data([],[])
			return

		bg_vals = interpolate(xy,self.bg_range,kind=self.bg_correct)
		self.bg.set_data(self.bg_range,bg_vals)
		

	def printdata(self):
		"""Prints stored data points to stdout"""  # TODO: make me a method on class Data()
		if not self.xy.any():
			print 'No stored coordinates.'
			return None

		print '---'
		if options.xrs:
			if self.d.has_esd:
				print '\nAttempting to interpolate standard deviations... for new stepco.inp\n'

				esds = interpolate(self.d.xye[:,0:3:2], self.xy[0], kind='linear')

				#print esds

			new_stepco_inp(self.xy,*options.xrs_out,esds=esds)
		else:
			for x,y in self.xy.transpose():
				print '%15.6f%15.2f' % (x,y)


class Lines(object):
	"""docstring for Lines"""
	def __init__(self, fig):
		super(Lines, self).__init__()
		self.fig = fig
		self.ax = self.fig.add_subplot(111)
		
		#self.fig.canvas.mpl_connect('pick_event', self.onpick)

	def onpick(self):
		"""General data point picker, should work for all kinds of plots?"""
		pass

	def plot(self,data):
		n = data.index

		colour = 'bgrcmyk'[n%7]

		ax = self.ax

		if options.nomove:
			dx, dy = 0, 0
		else:
			dx, dy = 8/72., 8/72.

		dx *= data.index
		dy *= data.index
		offset = transforms.ScaledTranslation(dx, dy, self.fig.dpi_scale_trans)
		transform = ax.transData + offset

		label = data.filename

		ax.plot(data.x,data.y,transform=transform,c=colour,label=label)

	def plot_tick_marks(self,data):
		ax = self.ax
		
		dx, dy = 0, -16/72.

		offset = transforms.ScaledTranslation(dx, dy, self.fig.dpi_scale_trans)
		transform = ax.transData + offset

		label = data.filename

		ax.plot(data.x,data.y,transform=transform,c='black',label=label,linestyle='',marker='|',markersize=10)
		#plt.plot(tck,np.zeros(tck.size) - (mx_dif / 4), linestyle='', marker='|', markersize=10, label = 'ticks', c='purple')


def setup_interpolate_background(d):
	print 'Interpolation mode for background correction\n'
	print 'The highest and lowest values are added by default for convenience. In the case that they are removed, only the values in the background range will be printed.'
	
	assert len(data) == 1, 'Only works with a single data file'
	
	x1 = data[0].x[0]
	x2 = data[0].x[-1]
	y1 = data[0].y[0]
	y2 = data[0].y[-1]
	
	#print x1,x2,y1,y2
	xy = np.array([[x1,y1],[x2,y2]],dtype=float)

	return Data(xy,name=' bg (--correct)')


def main(options,args):
	files = gen_read_files(args)
	data = [read_data(f) for f in files] # returns data objects
	fig = plt.figure()
		
	lines = Lines(fig)


	if options.xrs:
		fname = options.xrs
		copyfile(fname,fname+'~')
		f = read_file(fname)
		bg_data,options.xrs_out = parse_xrs(f)
	else:
		bg_data = None


	if options.bg_correct:
		bg_data = setup_interpolate_background(d)
		bg = Background(fig,d=bg_data,bg_correct=options.bg_correct) 
	elif options.backgrounder:
		bg = Background(fig,d=bg_data)


	if options.crplo:
		f_crplo()


	for d in reversed(data):
		lines.plot(d)


	if options.christian:
		assert bg_data, 'No background data available, can\'t use option --christian!'

		lines.plot(bg_data)
		f_plot_christian(bg_data.xy)


	if options.plot_ticks:
		ticks = load_tick_marks('hkl.dat')
		if ticks:
			lines.plot_tick_marks(ticks)


	if not sys.stdin.isatty():
		plot_stdin(fig)
	elif options.monitor:
		if options.monitor in ('crplot.dat','crplot'):
			f_monitor('crplot.dat',crplot_init,crplot_update,fig=fig)
		else:
			fn = options.monitor
			f_monitor(fn,plot_init,plot_update,fig=fig)
	else:
		plt.legend()
		plt.show()


	if options.bg_correct:
		f_bg_correct_out(d=data[0],bg_xy=bg.xy.T)




if __name__ == '__main__':
	usage = """"""

	description = """Notes:
- Requires numpy and matplotlib for plotting.
"""	
	
	epilog = 'Updated: {}'.format(__version__)
	
	parser = argparse.ArgumentParser(#usage=usage,
									description=description,
									epilog=epilog, 
									formatter_class=argparse.RawDescriptionHelpFormatter,
									version=__version__)
	
	
	parser.add_argument("args", 
						type=str, metavar="FILE",nargs='*',
						help="Paths to input files.")
		
#	parser.add_argument("-c", "--count",
#						action="store_true", dest="count",
#						help="Counts occurances of ARG1 and exits.")
#	
#
	parser.add_argument("-x", "--xrs", metavar='FILE',
						action="store", type=str, dest="xrs",
						help="xrs stepco file to open and alter")

	parser.add_argument("--crplo",
						action="store_true", dest="crplo",
						help="Mimics crplo -- plots observed, calculated and difference pattern and tick marks")

	parser.add_argument("-s", "--shift",
						action="store_false", dest="nomove",
						help="Slightly shift different plots to make them more visible.")
	
	parser.add_argument("-c", "--correct", metavar='OPTION',
						action="store", type=str, dest="bg_correct",
						help="Starts background correction routine. Only the first pattern listed is corrected. Valid options: 'linear','nearest','zero', 'slinear', 'quadratic, 'cubic') or as an integer specifying the order of the spline interpolator to use. Recommended: 'cubic'.")

	parser.add_argument("--christian",
						action="store_true", dest="christian",
						help="Special function for Christian. Plots the previous background and the background + the difference plot. Reads difference data from crplot.dat")

	parser.add_argument("-m", "--monitor", metavar='FILE',
						action="store", type=str, dest="monitor",
						help="Monitor specified file and replots if the file is updates. First 2 columns are plotted. Special value: crplot.dat")

	parser.add_argument("-t", "--ticks",
						action="store_true", dest="plot_ticks",
						help="Looks for local hkl.dat file and uses this to plot tick marks.")
	
	parser.add_argument("--stepco",
						action="store_true", dest="stepco",
						help="Shortcut for lines stepscan.dat -x stepco.inp")


	
	parser.set_defaults(backgrounder=True,
						xrs = None,
						nomove = True,
						bg_correct = False,
						crplo = False,
						christian = False,
						monitor = None,
						plot_ticks = False,
						stepco = False)
	
	options = parser.parse_args()
	args = options.args

	if options.stepco:
		options.xrs = 'stepco.inp'
		args = ['stepscan.dat']


	main(options,args)