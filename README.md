pullrequest-auto
================

'pullrequest-auto' python script automates code reviews of pull requests for a user-specified GitHub repository. Using the GitHub API, the script scans currently open pull requests for a specified project and reports whether or not the open pull request contain 'interesting items'. A report is printed via command line, containing interestingness, as well as what 'interesting item(s)' showed up and where. The script is configured to run to PuppetLabs specifications, but can be modified by editing 'interesting item(s)' in determine_interesting().
