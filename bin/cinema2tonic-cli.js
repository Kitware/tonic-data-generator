#! /usr/bin/env node

var fs = require('fs'),
    path = require('path'),
    usage = 'Usage: Cinema2Tonic /path/to/Cinema/DataSet/directory';

// Make sure we have valid argument
if(process.argv.length !== 3) {
    console.log(usage);
    return;
}

// Load Tonic descriptor
var cinemaDescriptor = require(process.argv[2] + '/info.json');

// Find the possible type mapping
if(cinemaDescriptor.metadata.type === 'parametric-image-stack') {
    // Spec A
    require('../javascript/tonic-cinema-spec-a').tonic(cinemaDescriptor, process.argv[2]);
} else {
    console.log('The following Cinema database can not be converted into Tonic dataset.');
    console.log('=>', cinemaDescriptor.type);
}
