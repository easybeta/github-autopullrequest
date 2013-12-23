'''
pullrequest-auto.py - Created by Eric Betancourt [betancourt.eric.s@gmail.com]

Write a program that will help automate code reviews of pull requests to our GitHub 
repositories. We are command line people, so this should be a command line application, 
but you can write it in whatever language and using whatever libraries you think are best. 
Show us the way that you think software should be written. The minimum that we expect is 
that it will work.

Using the GitHub api (documented at https://api.github.com/) write a program that will 
scan the currently open pull requests for a specified project and reports whether or not 
the open pull request contain 'interesting items', which will be explained below. Bonus 
points if the report also contains which 'interesting item(s)' showed up and where.

The Interesting Items:

Does not contain changes to any files in the 'spec/' directory

Any added or deleted lines contain the follow words (not as substrings of larger words):
/dev/null
raise
.write
%x
exec

Any change to the files
Gemfile
.gemspec

Example
> review puppetlabs/puppet
https://github.com/puppetlabs/puppet/pull/16663 - Interesting
https://github.com/puppetlabs/puppet/pull/16600 - Not Interesting
https://github.com/puppetlabs/puppet/pull/16598 - Not Interesting
'''
#! /usr/bin/python

import sys, re
import requests
import json

# Default Working Directory
working_dir = 'puppetlabs/puppet'

# Multiline compare checks n previous and upcoming lines around the line being compared.
def multiline_compare(array, idx, mod_idx, check_int):
	match = True
	check_count = -abs(check_int)
	
	while check_count <= abs(check_int):
		if array[idx + check_count] and array[mod_idx + check_count]:
			if array[idx + check_count] != array[mod_idx + check_count]:
				match = False
				break
		check_count = check_count + 1
		
	return match
				
# Determine line number for the modified code. Begin by checking the patch info line, if 
# the current line was just added, use the '+' start number, if the current line was 
# removed , use the '-' start number. Then parse through patch lines of code, incrementing
# the counter on each unmodified line, and on each '+' line (if current line was added), or
# on each '-' line (if current line was removed). 
def determine_line(patch_array, mod_symbol, mod_idx):
	line_count = 0
	
	for idx, line in enumerate(patch_array):
		if line[0] == '@':
			if mod_symbol == '+':
				line_count = int(re.match(r'.*\+([0-9]+),', line).group(1))
			else:
				mod_symbol = '-'
				line_count = int(re.match(r'.*-([0-9]+),', line).group(1))
			line_count = line_count - 1
		else:
			if (line[0] == ' ') or \
			   (line[0] == '+' and mod_symbol=='+') or \
			   (line[0] == '-' and mod_symbol=='-'):
				line_count = line_count + 1
		
		if line == patch_array[mod_idx]:
			if multiline_compare(patch_array, idx, mod_idx, 3):
				break

	return line_count

# Search Keywords by first loading in the modified files JSON data from github. Isolate 'patch'
# JSON data and search each modified line for each keyword using regular expressions,
# a match for the word plus any surrounding non-white characters is first captured.
# This captured string is then compared to the original keyword to verify that it's not a 
# substring. Line number is then determined and the appropriate description is written up
# to be displayed.
def search_keyword(html_request, keywords):
	keyword_found = False
	description = []
	idx = 0
	
	while True:
		try:
			repoItem = json.loads(html_request.text or html_request.content)[idx]
			patchItem = repoItem['patch'].encode('utf8').split('\n')

			line_idx = 0
			for line in patchItem:				
				for word in keywords:
					if word[0].isalpha(): # if keyword is standalone function
						search_string = '(\\S*%s\\S*)' % word
					elif word[0] == '.' or word[0] == '/': # if keyword is sub-function or directory
						search_string = '(%s\\w*)' % word
					else:
						search_string = word

					if line[0] == '+' or line[0] == '-':
						matches = re.findall(search_string, line, re.M)
						if matches:
							for match in matches:
								if match in word:
									line_num = determine_line(patchItem, line[0], line_idx)
									description.append("Found {'%s':'%s'} on line %d in %s" % (line[0], match, line_num, repoItem['filename']))
									#description.append('%s' % line)
									keyword_found = True
								#else: # Show failed matches (usually when keyword is sub-string)
									#print "%s - line %d - ['%s':'%s']\n%s - %s" % (repoItem['filename'], determine_line(patchItem, line[0], line_idx), match, word, line, match)
				line_idx = line_idx + 1
		except IndexError:
			break
		idx = idx + 1

	return keyword_found, description

# Check Filename by requesting modified files JSON data from github. Then search each 'filename' 
# entry in the  JSON pulls data.
def check_filename(html_request, filenames):
	name_found = False
	description = []
	idx = 0
	
	while True:
		try:
			repoItem = json.loads(html_request.text or html_request.content)[idx]
			for name in filenames:
				if name in repoItem['filename']:
					description.append('Located %s in %s' % (name, repoItem['filename']))
					name_found = True
		except IndexError:
			break
		idx = idx + 1
			
	return name_found, description

# Determine Interesting by first pulling pulls 'files' JSON Data. Then call sub-functions check_filename() 
# and search_keyword() to determine whether the pull is interesting.
def determine_interesting(pull_id):
	interest_found = 'Not Interesting'
	description = []

	try:
		html_request = requests.get('https://api.github.com/repos/%s/pulls/%d/files?page=%d&per_page=100' % (working_dir, pull_id, 1))
		if(html_request.ok and html_request.text != '[]'):
			# Any change to these files:
			file_names = ['Gemfile', '.gemspec']
			result, output = check_filename(html_request, file_names)
			if result == True:
				interest_found = 'Interesting'
				description.extend(output)

			# Does not contain changes to any files in the 'spec/' directory:
			dir_name = ['spec/']
			result, output = check_filename(html_request, dir_name)
			if result != True:
				interest_found = 'Interesting'
				description.append("No changes to files in the 'spec/' directory")

			# Any added or deleted lines contain the follow words (not as substrings of larger words):
			keywords = ['/dev/null', 'raise', '\.write', '%x', 'exec']
			result, output = search_keyword(html_request, keywords)
			if result == True:
				interest_found = 'Interesting'
				description.extend(output)
	except Exception as e:
		print "Error while executing pullrequest-auto.py during pull '%s/pulls/%d'." % (working_dir, pull_id)
		print e
			
	return interest_found, description 

# Main class determines what pulls are related to the working_dir. It then determines the interesting
# of each pull. Results with line number are then printed to the terminal.
def main(argv):
	global working_dir
	pageNum = 1
    
	if len(argv) > 1:
		working_dir = argv[1].strip("/")
		
	while True:
		try:
			r = requests.get('https://api.github.com/repos/%s/pulls?page=%d&per_page=100' % (working_dir, pageNum))
			if(r.ok and r.text != '[]'):
				
				print "Pull Request Urls - '%s' - Page %d:" % (working_dir, pageNum)
				idx = 0
				while True:
					try:
						repoItem = json.loads(r.text or r.content)[idx]
						pull_interest, interest_description = determine_interesting(repoItem['number'])
						print repoItem['url'] + ' - ' + pull_interest
						for line in interest_description:
							print '\t' + line				
					except IndexError:
						break
					idx = idx + 1
			else:
				match = re.search('\"message\":\"(.*)\",', r.text)
				if match:
					print "Unable to perform Pulls Request on '%s' - '%s'" % (working_dir, match.group(1))
				else:
					print "Pulls Requests Complete for '%s'." % working_dir
				break
		except Exception as e:
			print "Error while executing pullrequest-auto.py with directory '%s'." % working_dir
			print e
			break
		pageNum = pageNum + 1

if __name__ == '__main__':
    main(sys.argv)
