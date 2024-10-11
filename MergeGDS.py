#! /bin/env python3.7
import os,sys,shutil
import argparse

if len(sys.argv) <=1 :
   print('''
Notice:
    mode1: syntax: mergeGDS gds1 gds2 gds3
           return  gds1_merge.gds
           function:merge gds2 gds3 into gds1's top cell

    mode2: syntax: mergeGDS -t topname -m (X/Y) -s BBoxSpace -r lowLeft -d(debug) True -o outGDS -c center gds1 gds2 gds3 ....
           return: topname.gds
           function: merge gds1 gds2 gds3 into topname and keep a space between each bBox
                     -r , will move gds1 gds2 gds3 originXY to lowLeft bBox
                     -c , will move outGDS originXY to center bBox
''')

parser = argparse.ArgumentParser()
parser.add_argument("-t","--topname")
parser.add_argument("-m","--mode",choices=["X","Y"])
parser.add_argument("-s","--space")
parser.add_argument("-o","--outGds")
parser.add_argument("-d","--debug")
parser.add_argument("-r","--origin",choices=["lowLeft"])
parser.add_argument("-c","--outOrigin",choices=["center","lowLeft"])
parser.add_argument("gds",nargs='+')

args = parser.parse_args()

argDict ={}
if args.mode == "X": mode="tileX"
if args.mode == "Y": mode="tileY"

if args.topname: argDict["topName"]     = args.topname
if args.mode   : argDict["mode"]        = mode
if args.space  : argDict["space"]       = args.space
#if args.outOrigin: argDict["outOrigin"] = args.outOrigin

#IMCPdir = "/home/xxchen/work/important/script/SplitMask/modify/"
IMCPdir = "/apps/imctf/cad/script/SplitMask/splitMask/script/"
sys.path.append(IMCPdir)

from IMCP import *

def utPathRmDir(*argvs):
    for path in argvs:
        filePath = os.path.abspath(path)
        if os.path.isfile(filePath):
           os.remove(filePath)
           print("removed file:"+str(filePath))
        elif os.path.isdir(filePath):
           shutil.rmtree(filePath,True)
           print("removed dir: "+str(filePath))

def calMergeGds2(gdsList,outGDS,runDir,topName="",mode="orign",space="",x=0,y=0):
    '''
Usage   : Merge gds list
       calMergeGds(gdsList,outGDS,runDir,topName="",mode="orign",space=100)
                [str,,]  str     str        str      str           int 

        mode  = "orign" or "tileX" or "tileY" or "xy" 
        space = int (when use mode,must give a space)
       
       return result
              0 or 1
       (the gds don't need have the same topcell)
Author  : Bill
Version : 1.2
Data    : 2021-04-07
'''
#create top for all gds
    gdsPath1 = gdsList[0]
    if isinstance(gdsPath1,list) : gdsPath1 = gdsPath1[0]
    if not topName : 
           topName = calGetGdsTop(gdsPath1) 
    tclPath = runDir + topName + "_merge.tcl"
    logPath = runDir + topName + "_merge.log"
    FO = open(tclPath,"w") 
    FO.write("layout filemerge \\\n")

    if mode == "orign":
          gdsTopList = []
          for gdsPath in gdsList:
              if calGdsCellExist(gdsPath,topName):
                 gdsTopList.append(gdsPath)
              else: 
                 gdsTopList.append(calGdsCellCreateTop(gdsPath,runDir,topName))          
          for gdsPath in gdsTopList: 
              FO.write('-in %s \\\n' %gdsPath)
          #FO.write('-out %s -createtop %s_WB0 -mode rename -smartdiff  \n\nexit' %(outGDS,topName))
          #rename have some problem,will rename the topcell
          FO.write('-out %s \n\nexit' %outGDS)
    else:
          x,y = 0,0
          for gdsInfo in gdsList :
              if mode == "xy":
                 gdsPath,x1,y1=gdsInfo
                 x,y = x1*4000,y1*4000
              else:
                 gdsPath=gdsInfo

              FO.write("-infile [list -name %s -placecell [list -x %d -y %d]] \\\n" %(gdsPath,x,y))
              none,lenX,lenY = calGetGdsBox(gdsPath)
              
              if mode == "tileX":
                 if not space : print("You must give a space,when not use mode=tileX/tileY")
                 x = int(space)*4000 + lenX + x
              if mode == "tileY":
                 if not space : print("You must give a space,when not use mode=tileX/tileY")
                 y = int(space)*4000 + lenY + y
               
          FO.write('-createtop %s -out %s -mode rename -smartdiff \n\nexit' %(topName,outGDS))
       
    FO.close()
    line = "Merge GDS for %s" %topName
    cmd  = "calibredrv -shell %s > %s" %(tclPath,logPath)
    return utSystem(cmd,runDir,line)

def calMoveOrigin(gdsList,runDir,mode):
    if runDir[-1] != "/": runDir = runDir+"/"
    runDir  = runDir + "moveOrigin/"
    tclPath = runDir + "moveOrigin.tcl"  
    logPath = runDir + "moveOrigin.log"  
    utPathMakeDir(runDir)

    rList = []
    FO = open(tclPath,"w")
    for gdsPath in gdsList:
        gdsName = gdsPath.split("/")[-1]
        gdsOut  = runDir + gdsName
        FO.write("set lay [layout create %s -dt_expand]\n" %gdsPath) 
        FO.write("set topcell [$lay topcell]\n")
        FO.write("set box [$lay bbox $topcell]\n")
        if mode == "lowLeft":
           FO.write("$lay modify origin $topcell [lindex $box 0] [lindex $box 1]\n" )
        if mode == "center":
           FO.write("$lay modify origin $topcell [expr ([lindex $box 0]+[lindex $box 2])/2.0] [expr ([lindex $box 1]+[lindex $box 3])/2.0]\n" )

        FO.write("$lay gdsout %s\n\n" %gdsOut)
        rList.append(gdsOut) 

    FO.close()
    line = "move GDS Origin" 
    cmd  = "calibredrv -shell %s > %s" %(tclPath,logPath)
    utSystem(cmd,runDir,line)
    return rList

runDir = os.getcwd() + "/merge_temp/"
if len(args.gds) >=2: 
   gdsList = args.gds 
   topgds  = gdsList[0]

   if args.mode:
      if args.outGds:
         mergegds = args.outGds
      else:
         mergegds = args.topname + ".gds"   
   else:
      mergegds = topgds.split(".gds")[0] + "_merge.gds"
      
   print("the mergegds is :%s"  %mergegds) 
   
   utPathMakeDir(runDir)
   gdsList = [ os.path.abspath(x) for x in gdsList]
   print("gdsList is:")
   for gds in gdsList:
       print(gds)

   if args.origin:  
      gdsList = calMoveOrigin(gdsList,runDir,"lowLeft") 

   calMergeGds2(gdsList,mergegds,runDir,**argDict)

   if args.outOrigin:
      print("Success move mergeGDS origin to : %s" %args.outOrigin)
      ogds  = runDir+mergegds 
      mergegds, = calMoveOrigin([ogds],runDir,args.outOrigin)
      print("outOrigin result:",mergegds)
      cmd = "/bin/mv -f %s %s" %(os.path.abspath(mergegds),os.getcwd())
   else: 
      cmd = "/bin/mv -f %s %s" %(os.path.abspath(runDir+mergegds),os.getcwd())

   utSystem(cmd,os.getcwd(),"move to ./")
   if not args.debug:
      utPathRmDir(runDir)


