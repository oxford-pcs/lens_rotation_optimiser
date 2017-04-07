class Controller():
  def __init__(self, zmx_link):
    self.zmx_link = zmx_link
    
  def _updateDDE(self):
    self.zmx_link.zOptimize(numOfCycles=-1)
    self.zmx_link.zGetUpdate()
    
  def DDEToLDE(self):
    self._updateDDE()
    self.zmx_link.zPushLens()

  def LDEToDDE(self):
    self.zmx_link.zGetRefresh()
    self._updateDDE()
    
  def addTiltAndDecentre(self, start_surface_number, end_surface_number, x_decentre, 
                         y_decentre, x_tilt, y_tilt):
    cb1, cb2, dummy = self.zmx_link.zTiltDecenterElements(start_surface_number, 
                                                          end_surface_number, 
                                                          xdec=x_decentre, 
                                                          ydec=y_decentre, 
                                                          xtilt=x_tilt, 
                                                          ytilt=y_tilt)
    self.DDEToLDE()
    return (cb1, cb2, dummy)
  
  def delMFOperand(self, row_number):
    self.zmx_link.zDeleteMFO(row_number)
    
  def findSurfaceNumberFromComment(self, comment):
    for surface_number in range(1, self.getSystemData().numSurf+1):
      if comment in self.getSurfaceComment(surface_number):
        return surface_number
    
  def getSurfaceComment(self, surface_number):
    return self.zmx_link.zGetSurfaceData(surface_number, self.zmx_link.SDAT_COMMENT) 
  
  def getSurfaceDecentreX(self, surface_number):
    return self.zmx_link.zGetSurfaceParameter(surface_number, 1)
  
  def getSurfaceDecentreY(self, surface_number):
    return self.zmx_link.zGetSurfaceParameter(surface_number, 2)
  
  def getSurfaceTiltX(self, surface_number):
    return self.zmx_link.zGetSurfaceParameter(surface_number, 3)
  
  def getSurfaceTiltY(self, surface_number):
    return self.zmx_link.zGetSurfaceParameter(surface_number, 4)

  def getSystemData(self):
    return self.zmx_link.zGetSystem()
    
  def getThickness(self, surface_number):
    return self.zmx_link.zGetSurfaceData(surface_number, self.zmx_link.SDAT_THICK)
  
  def loadFile(self, path):
    self.zmx_link.zLoadFile("C:\Users\\barnsley\Google Drive\camera70_empirical.ZMX")
    self.zmx_link.zPushLens()
    
  def loadMF(self, filename):
    self.zmx_link.zLoadMerit(filename)

  def optimise(self, nCycles=0):
    mf_value = self.zmx_link.zOptimize(numOfCycles=nCycles, algorithm=0, timeout=None)
    return mf_value    
  
  def saveMF(self, filename):
    self.zmx_link.zSaveMerit(filename)
    
  def setComment(self, surface_number, comment, append=False):
    if append:
      old_comment = self.getSurfaceComment(surface_number)
      if old_comment is not "":
        comment = comment + ';' + old_comment
    self.zmx_link.zSetSurfaceData(surface_number, self.zmx_link.SDAT_COMMENT, comment)
    self.DDEToLDE()
    
  def setSurfaceDecentreX(self, surface_number, value):
    return self.zmx_link.zSetSurfaceParameter(surface_number, 1, value)
  
  def setSurfaceDecentreY(self, surface_number, value):
    return self.zmx_link.zSetSurfaceParameter(surface_number, 2, value)
  
  def setSurfaceTiltX(self, surface_number, value):
    return self.zmx_link.zSetSurfaceParameter(surface_number, 3, value)
  
  def setSurfaceTiltY(self, surface_number, value):
    return self.zmx_link.zSetSurfaceParameter(surface_number, 4, value)    
    
  def setThicknessSolveVariable(self, surface_number):
    self.zmx_link.zSetSolve(surface_number, self.zmx_link.SOLVE_SPAR_THICK, self.zmx_link.SOLVE_CURV_VAR)
    self.DDEToLDE()
  
    
