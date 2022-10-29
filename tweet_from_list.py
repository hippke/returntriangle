import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import datetime
import yfinance as yf
import requests
import re
import random
import csv
import pandas as pd
from bs4 import BeautifulSoup
from twython import Twython
from numba import jit


def get_symbol_and_handle_from_list(url):
	l = pd.read_csv(url, sep=",").values.tolist()
	symbol, twitter_handle = random.choice(l)
	return symbol, twitter_handle


def get_symbol(url):
    tag = "data-symbol="
    max_length_symbol = 20
    soup = str(BeautifulSoup(requests.get(url).text, 'lxml'))
    y = [m.start() for m in re.finditer(tag, soup)]
    list_symbols = []
    for pos in y:
        s = soup[pos+len(tag)+1:pos+len(tag)+max_length_symbol]
        s = s.partition("\"")[0]
        list_symbols.append(s)
    list_symbols = list(dict.fromkeys(list_symbols))
    return random.choice(list_symbols) 


@jit(nopython=True)
def CAGR(ratio, time):
	return 100 * (ratio ** (1 / time) - 1)


@jit(nopython=True)
def triangle(dates, values):
	l = len(values)
	matrix = np.zeros((l, l))
	for i in range(l):
		for j in range(i+1, l):
			time = dates[j] - dates[i]
			ratio = values[j] / values[i]
			if values[i] > 0 and time > 0:
				matrix[j, i] = CAGR(ratio, time)
	return matrix


APP_KEY = os.environ.get('CONSUMER_KEY')
APP_SECRET = os.environ.get('CONSUMER_SECRET')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.environ.get('ACCESS_TOKEN_SECRET')
twitter = Twython(APP_KEY, APP_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
#print(twitter.verify_credentials())

image = "triangle.png"
url = "https://raw.githubusercontent.com/hippke/returntriangle/main/list.csv"

try:
	symbol, twitter_handle = get_symbol_and_handle_from_list(url)
	print("symbol, twitter_handle:", symbol, twitter_handle)
	short_name = yf.Ticker(symbol).info["shortName"]
	period = "max" 
	print("Getting data for", str(short_name))
	hist = yf.Ticker(symbol).history(period=period)
	decimal_dates = (hist.index.year + (hist.index.dayofyear - 1) / 365).to_numpy()
	values = hist.loc[:,"Close"].to_numpy()
	print("Symbol OK")
	print("Got data")
	print("Data points:", len(values))
	print("Time span (years):", max(decimal_dates) - min(decimal_dates))

	#plt.plot(dates, values)
	#plt.yscale("log")
	#plt.xlabel("Year")
	#plt.ylabel("Value")
	#plt.show()

	print("Creating triangle")
	matrix = triangle(decimal_dates, values)
	print("Created triangle")

	# Rotate the matrix so that the sell date runs to the right, and buy upwards
	matrix = np.rot90(matrix)
	matrix = np.rot90(matrix)
	matrix = np.flipud(matrix)

	print("Making plot")
	fig, ax = plt.subplots()

	# Normalized color intensity in [1,99] percentile with 0-midpoint 
	divnorm = mcolors.TwoSlopeNorm(
		vmin=np.percentile(matrix, 0.5), 
		vcenter=0, 
		vmax=np.percentile(matrix, 99.5)
		)
	start_date = np.min(decimal_dates)
	end_date = np.max(decimal_dates)
	cax = plt.imshow(
		matrix, 
		interpolation='none', 
		cmap="seismic_r",  # diverging red to blue
		norm=divnorm, 
		extent=[start_date,end_date,start_date,end_date]
			)
	cbar = fig.colorbar(cax)
	cbar.ax.set_title('CAGR (%)')
	plt.grid(linestyle='--', linewidth=0.5)
	plt.title("Return triangle: \n" + str(short_name))
	plt.xlabel("Sell")
	plt.ylabel("Buy")
	ax.ticklabel_format(useOffset=False)
	#ax.legend(title='Made by @returntriangle', loc='upper left')
	plt.savefig(image, dpi=600, bbox_inches='tight')
	print("Plot made")

	print("Now posting status:")
	text = "Return triangle for " + str(short_name) + " #" + symbol + " " + twitter_handle
	print(text)

	response = twitter.upload_media(media=open(image, 'rb'))
	twitter.update_status(status=text, media_ids=[response['media_id']])
	print("Tweet sent. Script ends here. Goodbye.")
	plt.close()
	plt.clf()

except:
	print("Symbol NOK: no shortName found")
