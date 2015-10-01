#! /usr/bin/env node

var wrench = require('wrench'),
    pathToDeploy = process.argv[2] || process.env.TONIC_PYTHON_PATH;

if(pathToDeploy) {
    console.log(" => Deploying tonic Python module to directory: " + pathToDeploy);
    wrench.copyDirSyncRecursive(__dirname + '/../python/tonic',  pathToDeploy + '/tonic',{
        forceDelete: true
    });
} else {
    console.log("You need to provide an install path or configure it using your environment before running tonic-install-py");
    console.log();
    console.log(" => Using environment variable");
    console.log("  $ export TONIC_PYTHON_PATH=/path/to/python/path");
    console.log("  $ tonic-install-py");
    console.log();
    console.log(" => Using in-line path");
    console.log("  $ tonic-install-py /path/to/python/path");
    console.log();
}

