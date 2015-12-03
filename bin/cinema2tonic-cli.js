#! /usr/bin/env node

var fs = require('fs'),
    path = require('path'),
    usage = 'Usage: Cinema2Tonic /path/to/Cinema/DataSet/directory';

// Make sure we have valid argument
if(process.argv.length !== 3) {
    console.log(usage);
    return;
}

function ask(message, callback) {
    process.stdin.resume();
    process.stdin.setEncoding('utf8');
    process.stdout.write(message);
    process.stdin.on('data', function (text) {
        if(text[text.length - 1] === '\n') {
            process.stdin.pause();
            callback(text.substring(0, text.length - 1));
        }
    });
}

// Load Tonic descriptor
var cinemaDescriptor = require(process.argv[2] + '/info.json');

// Find the possible type mapping
if(cinemaDescriptor.metadata && cinemaDescriptor.metadata.type === 'parametric-image-stack') {
    // Spec A
    require('../javascript/tonic-cinema-spec-a').tonic(cinemaDescriptor, process.argv[2]);
} else if (cinemaDescriptor.associations) {
    // Assuming Spec B
    console.log('The selected Cinema database seems to be a SpecB. A more complex convertion will be needed.');
    ask('Please provide a destination directory\n => ', function(destPath){
        console.log('\nStart converting database into directory', destPath);
        require('../javascript/tonic-cinema-spec-b').tonic(cinemaDescriptor, process.argv[2], destPath);
    });
} else {
    console.log('The following Cinema database can not be converted into Tonic dataset.');
    console.log('=>', cinemaDescriptor.type);
}
