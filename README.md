openkim_melt_temperature
========================

The melting temperature test driver for OpenKIM.

Test Driver Layout:
The goal is to achieve a coexistence between solid and liquid at the Melting Temperature.  A check of the final phase is performed by analyzing the potential energy of the material and the MSD.

The simulation is setup with a long block of solid and a long block of liquid attached in the center.  

Prior to annealing:
```
  face                   Interface                  Inter
  |--------------------------|--------------------------|
  |                          |                          |
  |   Stable Solid Phase     | Quenched Liquid(?) Phase |
  |                          |                          |
  |--------------------------|--------------------------|
```

After annealing (under NPH):
```
  |-----------------------------------------------------|
  |                                                     |
  |               Unknown mixture of phases             |
  |                                                     |
  |-----------------------------------------------------|
```
This could be:
* all solid  (>90% solid)
* all liquid (>90% liquid)
* solid-liquid coexistence 
* A garbage mixture of bizarre junk
  * glass
  * a cluster of grain boundaries
  * who knows what

If succesful this test driver should create something like this:
```
   	         Interface                Interface
  |--------------|------------------------|-------------|
  |              |                        |             |
  |    Solid     |         Liquid         |   Solid     |
  |              |                        |             |
  |--------------|------------------------|-------------|
```

The interfaces should be mobile.  

Once coexistence is achieved the driver will spit out the corresponding cauchy-stress, temperature and a guess at the stable solid lattice constant (a).

So how do we achieve coexistence?  We guess at annealing temperatures until we stumble upon it. Start cold and grow hot.  

Psuedo code for test:
```
minT,maxT = 100,5100
bigTs = [minT ... maxT ... 500]
for trialT in bigTs:
    phase = checkCoexistence(trialT)
    
    if phase not allSolid (we've achieved melt):
       break

if phase == allSolid:
   ERROR: Melt never achieved, test is broken or potential never melts from this phase. Went up to MaxT
   exit

if phase == allLiquid:
   #Loop over a smaller temperature range now
   smallTs = [trialT-450 ... trialT-50 ... 50] 
   
   for trialT in smallTs:
       phase = checkCoexistence(trialT)

       if phase not allSolid (we've achieved melt):
           break

if phase == allLiquid:
   ERROR: Unable to achieve coexistence, went directly from solid to liquid, more precise testing required closest temperature is trialT.
   exit()

if phase == allSolid:
   ERROR: Melt never achieved, test is broken. Detected all liquid at liqT, but all solid at solT. Something goofy going on here.

#At this point we should have coexistence at trialT, but lets double check
finalPhase = checkCoexistenceHighResolution(trialT)

if finalPhase != coexistence:
   ERROR: Test failed at high resolution test. Closest melting temperature guess at trialT.

refined analysis based on thermodynamics()
generate clear log information()
copy all necessary log files()
clean up()
exit()
```

Once coexistence is found it is rerun with a bigger simulation and with longer anneal time to ensure a stable equilibrium has been achieved.  The final structures are analyzed and the results are spit out.


*** checkCoexistence(): ***
Inputs
* One configuration prior to annealing but immediately after the liquid is quenched, including potential energy per atom.
* Many (hundreds) of configurations after annealing
* The full thermodynamic profile (sans configurations) during the annealing run

Outputs
One of: ["Error","AllSolid","AllLiquid","Coexistence"]

