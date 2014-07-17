'''
github-autopullrequest.py - Created by Eric Betancourt [betancourt.eric.s@gmail.com]

This script helps automate code reviews of pull requests to a specified GitHub repositories.
Using the GitHub api (documented at https://api.github.com/) the script will scan the 
currently open pull requests for a specified working directory and reports whether or not 
the open pull request contain 'interesting items', which will be specified in config file 
titled "interesting-config.json".

Examples of Interesting Items:
- Any change to the specified files or directories
- Does not contain changes to any files in the specified directory
- Any added or deleted lines contain the follow words (not as substrings of larger words):
/dev/null
raise
.write

Example
> review cuckoobox/cuckoo
https://api.github.com/repos/cuckoobox/cuckoo/pulls/310 - Not Interesting
https://api.github.com/repos/cuckoobox/cuckoo/pulls/308 - Interesting
	Found {'+':'raise'} on line 30 in modules/processing/analysisinfo.py
	Found {'+':'raise'} on line 33 in modules/processing/analysisinfo.py
'''

#! /usr/bin/python

import sys, re
import requests
import json

# Default Configuration File
config_file = 'interesting-config.json'

# Default Working Directory
working_dir = []
verbose = True
interestingItems = []

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
                                    if verbose:
                                        description.append("Found {'%s':'%s'} on line %d in %s" % (line[0], match, line_num, repoItem['filename']))
                                        #description.append('%s' % line)
                                    keyword_found = True
                                #else: # Show failed matches (usually when keyword is sub-string)
                                    #if verbose:
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
def determine_interesting(pull_id, curr_working_dir):
    interest_found = 'Not Interesting'
    file_changes_good, file_changes_bad, line_keywords = [], [], []
    description = []
    
    for idx, item in enumerate(interestingItems):
        if item['type'] == 'fileChange' and item['modifyOk']:
            file_changes_good.append(item['keyword'])
        elif item['type'] == 'fileChange' and not item['modifyOk']:
            file_changes_bad.append(item['keyword'])
        elif item['type'] == 'lineKeyword':
            line_keywords.append(item['keyword'])
      
    try:
        html_request = requests.get('https://api.github.com/repos/%s/pulls/%d/files?page=%d&per_page=100' % (curr_working_dir, pull_id, 1))
        if(html_request.ok and html_request.text != '[]'):
            # Any change to these files or directories:
            result, output = check_filename(html_request, file_changes_good)
            if result == True:
                interest_found = 'Interesting'
                description.extend(output)

            # Does not contain changes to these files or directories:
            for fileentry in file_changes_bad:
                result, output = check_filename(html_request, fileentry)
                if result != True:
                    interest_found = 'Interesting'
                    description.append("No changes to entry %s" % fileentry)

            # Any added or deleted lines contain the follow words (not as substrings of larger words):
            result, output = search_keyword(html_request, line_keywords)
            if result == True:
                interest_found = 'Interesting'
                description.extend(output)
    except Exception as e:
        print "Error while executing github-autopullrequest.py during pull '%s/pulls/%d'." % (curr_working_dir, pull_id)
        print e
            
    return interest_found, description 

# Main class determines what pulls are related to the working_dir. It then determines the interesting
# of each pull. Results with line number are then printed to the terminal.
def main(argv):
    global working_dirs, verbose, interestingItems

    try:
        with open(config_file, 'r') as json_data:
            readin = json.load(json_data)
            working_dirs = readin['workingDirectory']
            verbose = readin['verbose']
            interestingItems = readin['interestingItems']
            if verbose:
                print 'Working Directory:'
                for idx, line in enumerate(working_dirs):
                    print '\t%s' % line['name']
                print 'Verbose:', verbose
                print 'Interesting Items:'
                for idx, line in enumerate(interestingItems):
                    print '\t%s - %s' % (line['type'], line['keyword'])
            json_data.close()
    except Exception as e:
        print e

    for idx, dir in enumerate(working_dirs):
        curr_dir = str(dir['name'])
        pageNum = 1
        while True:
            try:
                r = requests.get('https://api.github.com/repos/%s/pulls?page=%d&per_page=100' % (curr_dir, pageNum))
                if(r.ok and r.text != '[]'):
                    print "Pull Request Urls - '%s' - Page %d:" % (curr_dir, pageNum)
                    idx = 0
                    while True:
                        try:
                            repoItem = json.loads(r.text or r.content)[idx]
                            pull_interest, interest_description = determine_interesting(repoItem['number'], curr_dir)
                            print repoItem['url'] + ' - ' + pull_interest
                            for line in interest_description:
                                print '\t' + line                
                        except IndexError:
                            break
                        idx = idx + 1
                else:
                    match = re.search('\"message\":\"(.*)\",', r.text)
                    if match:
                        print "Unable to perform Pulls Request on '%s' - '%s'" % (curr_dir, match.group(1))
                    else:
                        print "Pulls Requests Complete for '%s'." % curr_dir
                    break
            except Exception as e:
                print "Error while executing github-autopullrequest.py with directory '%s'." % curr_dir
                print e
                break
            
            pageNum = pageNum + 1

if __name__ == '__main__':
    main(sys.argv)
