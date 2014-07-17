github-autopullrequest.py
================

This script helps automate code reviews of pull requests to a specified GitHub repositories.
Using the GitHub api (documented at https://api.github.com/) the script will scan the 
currently open pull requests for a specified working directory and reports whether or not 
the open pull request contain 'interesting items', which will be specified in config file 
titled "interesting-config.json".

Examples of Interesting Items:
- Any change to the specified files
- Does not contain changes to any files in the specified directory
- Any added or deleted lines contain the follow words (not as substrings of larger words): <br>
/dev/null<br>
raise<br>
.write

Example:
> review puppetlabs/puppet <br>
> https://api.github.com/repos/cuckoobox/cuckoo/pulls/310 - Not Interesting<br>
> https://api.github.com/repos/cuckoobox/cuckoo/pulls/308 - Interesting<br>
> &nbsp&nbsp&nbsp Found {'+':'raise'} on line 30 in modules/processing/analysisinfo.py<br>
> &nbsp&nbsp&nbsp Found {'+':'raise'} on line 33 in modules/processing/analysisinfo.py
