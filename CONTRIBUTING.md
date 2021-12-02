# Contributing to Lingvodoc

## Table of contents
* [Repositories responsibility](#repositories-responsibility)
* [Contribution guides](#contribution-guides)

## Repositories responsibility

The are two repositories for Clouni project:

* [Base repository](https://github.com/ispras/clouni). It contains all the python code.
* [Documentation repository](https://github.com/bura2017/clouni.github.io). It contains all documentation source
* The only bug-tracker is located [here](https://github.com/ispras/clouni/issues) for both repos.

## Contribution guides

1. Create an issue in corresponding repository. **Each** implemented feature or bug must have separate issue.
2. The issue **must** contain the following information:
    * For all the types of issues you should fill up **steps to reproduce**.
        * Clouni CLI command which was executed 
        * TOSCA template which was passed as input template. Include custom TOSCA types if ones were used
        * Actual current result of command execution
        * Desired or expected result of command execution
3. If you have created a bug-report wait for our response please.
4. Create **new branch** for your feature or fix. If you have no write permissions, make fork first and then create a branch in your forked repository  
5. Make sure you have you branch updated with new commits in master. Make updates with rebase
   
`git rebase master`

5. Before sending pull-request you **must** synchronize and rebase your branch with master. And ensure that it would be possible if you are planning to send a batch of pull requests.
6. Try to make commits in such a way that would make possible to separate pull requests by issues they are supposed to close. If it's not possible, that's not critical, but just give a try at least please.
7. Write tests for your new feature, use current tests as an example
8. **Test** your feature or fix
9. Make a pull request to master branch
10. **Wait** for [Admin](https://github.com/bura2017) to check and accept your pull request please.

