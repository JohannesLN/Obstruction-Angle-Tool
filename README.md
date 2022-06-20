# Obstruction-Angle-Tool
An ESRI ArcGIS Pro Toolbox that calculates obstruction angles of windows using 3D window data and a DSM.

ESRI Toolbox verison: 10.5/10.6 Toolbox (Copyright 2022 Esri)

How to run tool:
  1. Add "OA_Calculator_toolbox.tbx" to ESRI ArcGIS Pro
  2. Right click on the toolbox's script and add your own script file location for "OA_tool.py"
  3. Open the toolbox in ArcGIS Pro like any other geoprocessing tool
  4. Add a File Geodatabase Feature Class (Geometry type: Multipatch) with the 3D window data you want to calculate the obstruction angle of. 
  5. Add a digital surface model of the area around the windows. 
  6. Choose a output path (geodatabase) 
  7. Run the tool. 

Output: A point at each midpoint of the windows. These points' attribute table includes a column (OA) with the obstruction angle values, and other columns with information: Distance (from window to obstruction), grid_code (height of obstruction), Z_Mean (height of window midpoint), coordinates, and the search direction used.
If the tool is run with multiple windows as input data, it will merge the output to one layer. 

Image of the tools activity UML-diagram can be found in the "activity_uml_oa" file. 

More details about the entire project can be found in:
Nyborg, J.L., 2022: Geometric Comparison of 3D City Models for Daylight Simulations. MSc thesis, Department of Physical Geography and Ecosystem Science, Lund University
