#!/usr/bin/env python

import subprocess

def replaceString(inputText,oldString,newString):
    #Loops over the inputText, replaces oldString with newString
    return [line.replace(oldString,newString) for line in inputText]


def writeAndRun(lammpsInputFile, replacementVars,  MPIRanks = 1, debug = False):
    #Writes a lammps input file and runs it with MPI if appropriate
    #Returns the output from running LAMMPS.

    Tguess = replacementVars['runnerTemperatureGuess']
    lammpsToRunFile = "output/"+lammpsInputFile + "_" + Tguess

    #Generate the input file with corresponding variables
    lammpsOut = open(lammpsInputFile,"r").readlines()
    for oldVar, newVar in replacementVars.items():
        lammpsOut = replaceString(lammpsOut,oldVar,newVar)

    open(lammpsToRunFile,"w").writelines(lammpsOut)

    #Run Lammps
    if MPIRanks == 1:
        commandString = "lmp_g++ -in %s"%(lammpsToRunFile)
    else:
        commandString = "mpiexec -np %d lmp_g++ -in %s"%(MPIRanks,lammpsToRunFile)
    command = commandString.split()

    if debug:
        return open("output/log.lammps","r").readlines()
    else:
        return subprocess.check_output(command).split("\n")
        
