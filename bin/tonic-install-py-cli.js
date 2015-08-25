#! /usr/bin/env node

var wrench = require('wrench');

if(process.argv.length === 3) {
    wrench.copyDirSyncRecursive(__dirname + '/../python/tonic', process.argv[2] + '/tonic',{
        forceDelete: true
    });
} else {
    console.log("Usage: tonic-install-py destination_path");
}

