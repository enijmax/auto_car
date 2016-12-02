import cv2
import sys, getopt, os.path, time, datetime, math
from os import path, listdir, walk

def printHelp():
	print 'convert2Png.py -t <time in s> -f <filename>'
	sys.exit(2)

def getTimeStampFromFileName(fileName):
	return int(time.mktime(datetime.datetime.strptime(os.path.splitext(fileName)[0], "%Y-%m-%d_%H-%M-%S").timetuple()) * 1000)

# find closest filename.
def findNearByVideo(ts, folder="."):
	closest_vdo_filename = ''
	closest_vts = 0
	smallest_delta = -1
	for vdofile in listdir(folder):
		if vdofile.endswith('.mp4'):
			#print vdofile
			vts = getTimeStampFromFileName(vdofile)
			delta = math.fabs(vts - ts)
			if smallest_delta == -1:
				smallest_delta = delta
				closest_vdo_filename = vdofile
				closest_vts = vts
			elif smallest_delta > delta:
				smallest_delta = delta
				closest_vdo_filename = vdofile
				closest_vts = vts
	return [closest_vdo_filename, closest_vts]

# Main Start here #
def main(argv):
	timeInMs = 0
	vdo_file = ''
	vdo_ts = 0

	forward_num = 0
	left_num = 0
	right_num = 0
	try:
		opts, args = getopt.getopt(argv, "ht:f:", [])
	except getopt.GetoptError:
		printHelp()

	for opt, arg in opts:
		if opt == '-h':
			printHelp()
		elif opt in ('-t'):
			timeInMs = int(arg) * 1000	
		elif opt in ('-f'):
			vdo_file = arg

	if os.path.isfile(vdo_file) == False:
		print 'File %s is not existed'%vdo_file
		return

	print 'video file is "' + vdo_file + '", capture at ' + str(timeInMs)

	# read video 
	vidcap = cv2.VideoCapture(vdo_file)
	frame_ts = 0

	frame = None

	# Seeking the frame
	vidcap.set(0, timeInMs - 100)
	frame_ts = timeInMs - 100

	while timeInMs - frame_ts > -33:
		frame_ts += (1000/30)
		delta_t = math.fabs(frame_ts - timeInMs)
		if frame is not None and delta_t < 33:
			savename = vdo_file+"_"+str(frame_ts)
			print "save " + savename + ".png into file"
			cv2.imwrite(savename+'.png', frame)
		flag, frame = vidcap.read()
		if frame is not None:
			cv2.imshow('video', frame)
		else:
			print 'flag = ', flag

		# Press esc to quit the program
		if cv2.waitKey(1) == 27:
			break

	vidcap.release()
	return

if __name__ == "__main__":
	main(sys.argv[1:])