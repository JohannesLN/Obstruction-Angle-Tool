# Obstruction-Angle-Tool
An ESRI ArcGIS Pro Toolbox that calculates obstruction angles of windows using 3D window data and a DSM.

ESRI Toolbox verison: 10.5/10.6 Toolbox

How to run tool:
  1. Add "OA_Calculator_toolbox.tbx" to ESRI ArcGIS Pro
  2. Right click on the toolbox's script and add your own script file location for "OA_tool.py"
  3. Open the toolbox in ArcGIS Pro like any other geoprocessing tool
  4. Add a File Geodatabase Feature Class (Geometry type: Multipatch) with the 3D window data you want to calculate the obstruction angle of. 
  5. Add a digital surface model of the area around the windows. 
  6. Choose a output path (geodatabase) 
  7. Run the tool. 

Image of the workflow of the tool can be found in the "Workflow-ObstructionAngle.jpg" file. 
![OA_workflow](https://user-images.githubusercontent.com/11694862/169313162-de3648af-b636-4f92-9a2a-01e2832b6f2f.png)


More details about the entire project can be found in:
Nyborg, J.L., 2022: Geometric Comparison of 3D City Models for Daylight Simulations. MSc thesis, Department of Physical Geography and Ecosystem Science, Lund University
