#! /usr/bin/env node

require('shelljs/global');

var fs = require('fs'),
    path = require('path'),
    python = process.env.TONIC_PYTHON_EXEC,
    execNames = ['pvpython', 'vtkpython', 'python'];

function run() {
    var cmd = [ python ];
    for (var i = 2; i < process.argv.length; i++) {
        cmd.push(process.argv[i]);
    }
    exec(cmd.join(' '));
}

if(python) {
    run();
} else if (process.env.TONIC_PYTHON_PATH) {
    // Try to find the executable automatically
    var basePath = process.env.TONIC_PYTHON_PATH,
        found = false;
    for(var i = 0; i < 5 && !found; i++) {
        var execDir = path.join(basePath, 'bin');
        if(fs.existsSync(execDir)) {
            execNames.forEach(function(execName){
                python = path.join(execDir, execName);
                if(fs.existsSync(python)) {
                    found = true;
                    run();
                }
            });
        } else {
            // Try parent directory
            basePath = path.dirname(basePath);
        }
    }
    if(!found) {
        console.log(' => Impossible to find the python executable based on the TONIC_PYTHON_PATH variable. Please set TONIC_PYTHON_EXEC variable.');
    }
} else {
    console.log(' => tonic-run-js expect either TONIC_PYTHON_PATH or TONIC_PYTHON_EXEC environment variable to be set');
}
