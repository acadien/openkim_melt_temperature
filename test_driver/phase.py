#!/usr/bin/env python

from scipy import ndimage
import numpy as np
import pylab as pl
#local
from KIMception import * #exceptions
import parser
from meanSquareDist import meanSquareDistRefAtom

def sliceBin(Zs,Vals,nBin):
    #Zs: Z fractional coordinates, 
    #Vals: corresponding value for atom with Zs coordinate
    #nBins: how many bins to generate
    #returns the average value in each slice

    binnedZ = [int(z*nBin) for z in Zs]
    bins = [float(b)/nBin for b in sorted(list(set(binnedZ)))]
    vals = ndimage.measurements.mean(Vals,labels=binnedZ,index=np.unique(binnedZ))
    return bins,vals

def deriv(h,vals):
    #Derivative of a looped list
    return [(vals[i] - vals[i-1])/h for i in range(len(vals))]

def windowAvg(a,n=5):
    #A simple window average
    a = list(a)
    m = len(a)
    b = a+a+a
    return np.convolve(b, np.ones(n)/n,mode='same')[m:2*m]

def MSDbyAtom(allConfigs):
    #Mean Square Displacement calculated per atom 
    #atoms are in fractional coordinates

    lengths = np.array([[0,1],[0,1],[0,1]])
    delt,msdAtom = meanSquareDistRefAtom(allConfigs,0,len(allConfigs[0]),len(allConfigs),lengths)
    return list((msdAtom.T)[-1])


def phaseBoundsByPE(Zs,PEs,liqPE,solPE,logName=None):
    #Given the fractional Z coordinates, PE per atom and 
    #average PE for the liquid/solid phase
    #this function returns a guess as to the location of the
    #solid liquid phase boundaries, assumes only 2 phase boundaries

    nbins = 50
    zBins,zPE = sliceBin(Zs,PEs,nbins)
    zPEsmooth = windowAvg(zPE,5)
    zPEprime = windowAvg(deriv(zBins[1]-zBins[0],zPEsmooth)).tolist()
    if logName!=None:
        convert = lambda x: " ".join(map(str,x))+"\n"
        zlog = ["Z coord ($\AA$), Average PE (eV)\n"]+map(convert,zip(zBins,zPE))
        open(logName,"w").writelines(zlog)

    boundIndex1 = zPEprime.index(min(zPEprime))
    boundIndex2 = zPEprime.index(max(zPEprime))
    lowerBoundIndex = min(boundIndex1,boundIndex2)
    upperBoundIndex = max(boundIndex1,boundIndex2)
    phase1Width = upperBoundIndex-lowerBoundIndex
    phase2Width = nbins - phase1Width
    p1perc = int(float(phase1Width)/nbins*100)
    p2perc = int(float(phase2Width)/nbins*100)
    lowbperc = float(lowerBoundIndex)/nbins
    uppbperc = float(upperBoundIndex)/nbins
    phase1PE = sum(zPE[lowerBoundIndex:upperBoundIndex])/phase1Width
    phase2PE = (sum(zPE[upperBoundIndex:])+sum(zPE[:lowerBoundIndex]))/phase2Width

    #phase PE must be within 3 percent of actual solid or liquid PE
    errorBound = 0.04 

    #Error checking
    liq1Err = np.fabs(phase1PE - liqPE) / np.fabs(phase1PE)
    liq2Err = np.fabs(phase2PE - liqPE) / np.fabs(phase2PE)
    sol1Err = np.fabs(phase1PE - solPE) / np.fabs(phase1PE)
    sol2Err = np.fabs(phase2PE - solPE) / np.fabs(phase2PE)

    #print liq1Err,sol1Err
    #print liq2Err,sol2Err

    if sol1Err < liq1Err and sol2Err < liq2Err:
        raise KIMTestError("It appears the entire simulation is solid, should rerun with higher starting temperature")
    if sol1Err > liq1Err and sol2Err > liq2Err:
        raise KIMTestError("It appears the entire simulation is liquid, should rerun with lower starting temperature")
    
    solPerc,liqPerc = -1,-1
    if sol1Err < liq1Err and sol2Err > liq2Err:
        solPerc = p1perc
        liqPerc = p2perc
    elif sol1Err > liq1Err and sol2Err < liq2Err:
        solPerc = p2perc
        liqPerc = p1perc
    else:
        raise KIMTestError("Unable to tell which phase is solid/liquid based on Potential Energy")

    #Print out results, all pretty like for those nice KIM users
    print "="*50
    print "=== S-L Phase Boundary Tracker: Potential Energy"
    print "="*50
    print "        Solid Liquid Amount BoundLocat."
    print "phase1: %s  %s  %d%s     %2.2f"%(sol1Err<errorBound,liq1Err<errorBound,p1perc,"%",lowbperc)
    print "phase2: %s  %s  %d%s     %2.2f"%(sol2Err<errorBound,liq2Err<errorBound,p2perc,"%",uppbperc)
    print "="*50

    return lowerBoundIndex, upperBoundIndex, solPerc, liqPerc


def checkCoexistence(filesToParse, filesToLog, debug = False, T = None):
    #Track the Phase Boundary using Potential Energy and MSD
    #Returns one of ["Error","AllSolid","AllLiquid","Coexistence"]

    initialDumpFile, finalDumpFile, lammpsThermoDataFile = filesToParse 
    dataDumpFile, thermoDumpFile, ZPEFinallog = filesToLog
    
    #Start by parsing all of the data provided.

    #Thermodynamics (vs time)
    lammpsThermoData = open(lammpsThermoDataFile,"r").readlines()
    annealThermo,annealStartI = parser.parseThermo(lammpsThermoData,"Step Temp Press Volume TotEng Lx Pxx Pyy Pzz Pxy Pxz Pyz")
    annealThermo[0] = map(int,annealThermo[0])  #Steps should be ints

    #Grab the atomic configuration from pre-anneal
    initialDump = open(initialDumpFile,"r").readlines()
    boundsInitTS,atomsInitTS = parser.parseDump(initialDump)

    #Grab the PE from post-anneal (101x total)
    finalDump = open(finalDumpFile,"r").readlines()
    boundsFinalTS,atomsFinalTS = parser.parseDump(finalDump)

    #Atomic locations in fractional coordinates
    ids,types,Xs,Ys,Zs,PEs = atomsInitTS[0]
    PEInit = list(PEs)
    ZInit = list(Zs)
    
    #Atomic locations in fractional coordinates
    ZFinals,PEFinals,atomFinals = list(),list(),list()
    for i in atomsFinalTS:
        atomFinals.append(zip(i[2],i[3],i[4]))
        ZFinals.append(i[4])
        PEFinals.append(i[5])

    # Log stuff before processing and error checking so logs exist if test exits early. 

    if not debug:
        #Write Thermodynamic data during the heat/quench/anneal process
        thermoData=["Step Temp Press Volume TotEng Lx Pxx Pyy Pzz Pxy Pxz Pyz\n"]+map(lambda x: " ".join(map(str,x))+"\n",zip(*annealThermo))
        open(thermoDumpFile,"w").writelines(thermoData)

        #Write Final configuration with atomic coordinates and potential energy
        configData=["ID Species X Y Z PE\n"]+map(lambda x: " ".join(map(str,x))+"\n",zip(*atomsFinalTS[-1]))
        open(dataDumpFile,"w").writelines(configData)

    #############################################################
    #### Find the Liquid and Solid average potential energies ###
    #############################################################

    #The initial boundary should be stationary at halfZ
    #Solid is lower half, liquid is upper half
    halfZ = 0.5
    solidEnergy, liquidEnergy = 0.0, 0.0
    solidCount, liquidCount = 0, 0
    for pe,z in zip(PEInit,ZInit):
        if z>halfZ:
            liquidCount += 1
            liquidEnergy += pe
        if z<halfZ:
            solidCount += 1
            solidEnergy += pe
    liquidPE = liquidEnergy/liquidCount
    solidPE = solidEnergy/solidCount

#    print T,liquidPE, solidPE, np.fabs(np.fabs(liquidPE)-np.fabs(solidPE))
#    msdAtom = MSDbyAtom(atomFinals)
#    print sum(msdAtom)/len(msdAtom)
#    nbins = 25
#    zBins,zMSD = sliceBin(ZInit,msdAtom,nbins)
#    zBins,zPE = sliceBin(ZInit,msdAtom,nbins)
#    pl.plot(zBins,zMSD)
    return ""
#    for i in range(len(atomsFinalTS)):
#        atomsFinalTS[i].append(msdAtom)
#    configData=["ID Species X Y Z PE MSD\n"]+map(lambda x: " ".join(map(str,x))+"\n",zip(*atomsFinalTS[-1]))
#    open("output/msd_"+str(T)+".dump","w").writelines(configData)
#    pl.show()
#    phaseBoundsByPE(ZInit,msdAtom,liquidPE,solidPE)
"""
    return ""

    #If solidPE == liquidPE it implies the entire simulation is liquid. Not possible for entire simulation to be solid before annealing.
    if np.fabs(liquidPE - solidPE)/np.fabs(liquidPE) < 0.03:
        raise KIMTestError("Liquid and Solid Potential Energies are nearly the same, this probably means everything has melted, restart with lower initial temperature. If this doesn't work then the Solid and Liquid PE are too simple and this test will not work.")
    exit(1)

    ################################
    ### PRE-ANNEAL PE PHASE TEST ###
    ################################

    #Check that you have a good initial bounds, also does error checking
    print "\nPRE ANNEAL TEST:"
    phaseBoundsByPE(ZInit,PEInit,liquidPE,solidPE)
    print "Note: Material should be exactly half liquid and half solid at this point (above)."
    print "\n"


    #################################
    ### POST-ANNEAL PE PHASE TEST ###
    #################################

    #Check the final bounds using PE
    ZFin = ZFinals[-1]         #Final Z fractional cooridnates
    PEFin = PEFinals[-1]       #Final per atom PE
    print "POST ANNEAL TEST:"
    pb1,pb2,solPerc,liqPerc = phaseBoundsByPE(ZFin,PEFin,liquidPE,solidPE,logName=ZPEFinallog)

    return ""
"""
