#!/usr/bin/env python

def parseThermo(thermoData,dataHeader):
    #Parses thermo_style data from lammps output, sticks it in column form
    #assumes all data are floats
    #column 0 of 'thermo' corresponds to dataHeader[0] data
    #returns thermo[header column]

    thermo = list()
    dataFoundFlag = False
    annealStart = -1
    for i,line in enumerate(thermoData):
        if dataFoundFlag:
            try:
                a = map(float,line.split())
                thermo.append(a)
            except ValueError:
                dataFoundFlag = False
        elif dataHeader in line:
            annealStart = i
            dataFoundFlag = True
    thermo = zip(*thermo)
    return thermo,annealStart

def parseDump(dumpData):
    #Returns the boundaries and atomic configurations from the lammps dump file
    #Sorts atoms by their ID
    #atomsTS containts id, species, xs, ys, zs in that order
    #boundsTS may include non-orthogonal info depending on simulation

    boundsTS = list() #The bounds at each time step (NPH has changing bounds)
    atomsTS = list() #The atomic coordinates at each time step
    boundsFoundFlag = False
    atomsFoundFlag = False
    for line in dumpData:
        if boundsFoundFlag:
            try:
                a = map(float,line.split())
                boundsTS[-1].append(a)
            except ValueError:
                boundsFoundFlag = False
        elif "ITEM: BOX BOUNDS" in line:
            boundsFoundFlag = True
            boundsTS.append(list())

        if atomsFoundFlag:
            try:
                a = map(float,line.split())
                atomsTS[-1].append(a) #id type xs ys zs
            except ValueError:
                atomsFoundFlag = False
                atomsTS[-1] = sorted(atomsTS[-1],key=lambda x:x[0])
                atomsTS[-1] = zip(*atomsTS[-1])
        elif "ITEM: ATOMS" in line:
            atomsFoundFlag = True
            atomsTS.append(list())

    #Clean up for last configuration
    if atomsFoundFlag:
        atomsTS[-1] = sorted(atomsTS[-1],key=lambda x:x[0])
        atomsTS[-1] = zip(*atomsTS[-1])

    return boundsTS,atomsTS


def grabNxyzLMP(lmpScript):
    #pulls out the number of basis copies from lammps input script in nx,ny,nz directions
    for line in lmpScript:
        if "region" in line and "box" in line:
            a = map(int,line.split("block")[-1].split()[:6])
            nx = a[1]-a[0]
            ny = a[3]-a[2]
            nz = a[5]-a[4]
            return nx,ny,nz
    return -1
