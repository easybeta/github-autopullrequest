pullrequest-auto
================

'pullrequest-auto' python script automates code reviews of pull requests for a user-specified GitHub repository. Using the GitHub API, the script scans currently open pull requests for a specified project and reports whether or not the open pull request contain 'interesting items'. A report is printed via command line, containing interestingness, as well as what 'interesting item(s)' showed up and where. The script is configured to run to PuppetLabs specifications, but can be modified by editing 'interesting item(s)' in determine_interesting().

Puppet Labs Interesting Items:

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
