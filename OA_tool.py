import arcpy
from sys import argv
from arcpy.sa import *


def OAcalc(windows, DSM, outputPath):  # OA Calc to tbx

    arcpy.env.overwriteOutput = True


    ### Save the coordinate system of the window data in a variable. It will be used in multiple tools later on.
    spatial_ref = arcpy.Describe(windows).spatialReference


    # Loop through each window in the input data
    wFields = ['OBJECTID', 'SHAPE@']  # The fields of the input windows that will be used
    with arcpy.da.SearchCursor(windows, wFields) as cursor:

        windowID = 1  # The ID given to each window - Value increases by one each loop
        windowOutputData = []  # A list that will store the results of each window, they will then be merged once all
        # windows have been visited

        for row in cursor:

            ### Find centroid point of Window ###
            arcpy.AddMessage("Calculating window {0}".format(windowID))

            # Process: Feature Vertices To Points (Feature Vertices To Points) (management)
            # Add points to each vertex of the input window
            windows_FVtP = arcpy.management.FeatureVerticesToPoints(in_features=row[1], point_location="ALL")

            # Process: Add Field (2) (Add Field) (management)
            # Add a field for the window ID (w_id)
            windows_add_wID = arcpy.management.AddField(in_table=windows_FVtP, field_name="w_id", field_type="SHORT",
                                                        field_precision=None, field_scale=None, field_length=None,
                                                        field_alias="w_id", field_is_nullable="NULLABLE",
                                                        field_is_required="NON_REQUIRED", field_domain="")[0]

            # Process: Calculate Field (7) (Calculate Field) (management)
            # Add the variable windowID to the window field w_id
            windows_calc_wID = \
                arcpy.management.CalculateField(in_table=windows_add_wID, field="w_id", expression=f"int({windowID})",
                                                expression_type="PYTHON3", code_block="", field_type="TEXT")[0]

            # Process: Points To Line (Points To Line) (management)
            # "Fill" the window by drawing lines from each vertex point. This will be used to find the centroid coord
            windows_p_to_lines = arcpy.management.PointsToLine(Input_Features=windows_calc_wID, Line_Field="w_id",
                                                               Sort_Field="", Close_Line="NO_CLOSE")

            # Process: Add Z Information (2) (Add Z Information) (3d)
            # Add a field to the data with the mean Z height (this is the same height the window has at its centre)
            windows_p_to_lines_zInfo = \
                arcpy.ddd.AddZInformation(in_feature_class=windows_p_to_lines, out_property=["Z_MEAN"],
                                          noise_filtering="")[
                    0]

            # Process: Add Fields (multiple) (2) (Add Fields (multiple)) (management)
            # Add two new fields where the coordinate of the centre point of the window will be stored
            windows_p_to_lines_addFields = arcpy.management.AddFields(in_table=windows_p_to_lines_zInfo,
                                                                      field_description=[
                                                                          ["cent_long_x", "DOUBLE", "", "", "", ""],
                                                                          ["cent_lat_y", "DOUBLE", "", "", "", ""]])[0]

            # Process: Calculate Geometry Attributes (Calculate Geometry Attributes) (management)
            # Calculate the centre coordinate in X and Y direction, then add it to the new fields from the previous step
            with arcpy.EnvManager(
                    outputCoordinateSystem=spatial_ref):
                windows_centroid_coord = \
                    arcpy.management.CalculateGeometryAttributes(in_features=windows_p_to_lines_addFields,
                                                                 geometry_property=[["cent_long_x", "CENTROID_X"],
                                                                                    ["cent_lat_y", "CENTROID_Y"]],
                                                                 length_unit="", area_unit="",
                                                                 coordinate_system=spatial_ref,
                                                                 coordinate_format="SAME_AS_INPUT")[0]

            # Process: XY Table To Point (XY Table To Point) (management)
            # Create points at the window centre location
            windows_centroid_points = arcpy.management.XYTableToPoint(in_table=windows_centroid_coord,
                                                                      x_field="cent_long_x", y_field="cent_lat_y",
                                                                      z_field="Z_Mean",
                                                                      coordinate_system=spatial_ref)
            ### ----------- end of group ----------- ###


            ### Find obstruction points and calculate the obstructio angle ###
            arcpy.AddMessage("Finding the obstruction points and calculating the obstruction angle...")
            # Process: Viewshed 2 (Viewshed 2) (3d)
            # Create a raster displaying what can be seen from the window centre
            # Changed property: inner_radius: Only look for cells further than 4 meters away from the window
            Output_above_ground_level_raster_2_ = ""
            Output_observer_region_relationship_table = ""
            viewshed = arcpy.ddd.Viewshed2(in_raster=DSM, in_observer_features=windows_centroid_points,
                                           out_agl_raster=Output_above_ground_level_raster_2_,
                                           analysis_type="FREQUENCY", vertical_error="0 Meters",
                                           out_observer_region_relationship_table=Output_observer_region_relationship_table,
                                           refractivity_coefficient=0.13, surface_offset="0 Meters",
                                           observer_elevation="Z_Mean", observer_offset="0 Meters",
                                           inner_radius="16 Meters", inner_radius_is_3d="GROUND", outer_radius="",
                                           outer_radius_is_3d="GROUND", horizontal_start_angle=0,
                                           horizontal_end_angle=360, vertical_upper_angle=90, vertical_lower_angle=-90,
                                           analysis_method="ALL_SIGHTLINES")

            # Process: Select Layer By Attribute (2) (Select Layer By Attribute) (management)
            # Only select the cells that can be seen (value = 1)
            viewshed_select = arcpy.management.SelectLayerByAttribute(in_layer_or_view=viewshed,
                                                                      selection_type="NEW_SELECTION",
                                                                      where_clause="Value > 0", invert_where_clause="")

            # Find field value of window height (to use in raster calculator)
            field_z = ['Z_Mean']
            windowHeight = 0
            with arcpy.da.SearchCursor(windows_centroid_points, field_z) as cursor2:
                for r in cursor2:
                    windowHeight = r[0]
                    break

            # The extract by mask and extract by attributes tools in the next lines are used to first find the DSM
            # cells within the viewshed and then only select the ones with higher values than the window Process:
            # Extract by Mask (Extract by Mask) (sa)
            find_high_elev_cells = arcpy.sa.ExtractByMask(in_raster=DSM, in_mask_data=viewshed_select)
            # Process: Extract by Attributes (Extract by Attributes) (sa)
            find_high_elev_cells2 = arcpy.sa.ExtractByAttributes(in_raster=find_high_elev_cells,
                                                                 where_clause="Value > {}".format(windowHeight))
            # Process: Raster to Point (Raster to Point) (conversion)
            with arcpy.EnvManager(outputMFlag="Disabled", outputZFlag="Disabled"):
                high_elev_points = arcpy.conversion.RasterToPoint(in_raster=find_high_elev_cells2, raster_field="VALUE")

            # Process: Add XY Coordinates (Add XY Coordinates) (management)
            # Add new XY coordinates to the window centres
            with arcpy.EnvManager(
                    outputCoordinateSystem=spatial_ref):
                windows_centroid_points_newZ_coords = arcpy.management.AddXY(in_features=windows_centroid_points)[0]

            # Process: Spatial Join (2) (Spatial Join) (analysis)
            # Join the table of the high elevation points (from the viewshed) and the window midpoints.
            highPoints_windows_join = arcpy.analysis.SpatialJoin(target_features=high_elev_points,
                                                                 join_features=windows_centroid_points_newZ_coords,
                                                                 join_operation="JOIN_ONE_TO_ONE", join_type="KEEP_ALL",
                                                                 match_option="CLOSEST", search_radius="",
                                                                 distance_field_name="Distance")

            # Process: Add Field (4) (Add Field) (management)
            # Adding a field where the obstruction angle (OA) value will be added
            highPointsAddField = \
                arcpy.management.AddField(in_table=highPoints_windows_join, field_name="OA", field_type="DOUBLE",
                                          field_precision=None, field_scale=None, field_length=None, field_alias="OA",
                                          field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED",
                                          field_domain="")[
                    0]

            ### ----------- end of group ----------- ###

            ## Search Direction (perpendicular to window) ###
            # Here the window vertices are used to find the direction the window is "looking"
            arcpy.AddMessage("Finding search Direction (perpendicular to window)...")

            # Process: Add Z Information (3) (Add Z Information) (3d)
            # Add Z information to the vertices
            windows_zInfo = \
                arcpy.ddd.AddZInformation(in_feature_class=windows_calc_wID, out_property=["Z"], noise_filtering="")[0]

            # Process: Select Layer By Attribute (3) (Select Layer By Attribute) (management)
            # Select the vertices that are greater than the mean height of the vertices. The point of this is to only
            # select vertices at the same height, before the angle between these points are then calculated later
            windows_zInfo_field = ['Z']
            windows_zInfo_mean = 0
            rowCounter = 0
            with arcpy.da.SearchCursor(windows_zInfo, windows_zInfo_field) as cursor3:
                for r3 in cursor3:
                    windows_zInfo_mean += int(r3[0])
                    rowCounter += 1
            windows_zInfo_mean = windows_zInfo_mean / rowCounter
            windows_zInfo_select = arcpy.management.SelectLayerByAttribute(in_layer_or_view=windows_zInfo,
                                                                           selection_type="NEW_SELECTION",
                                                                           where_clause="Z > {}".format(
                                                                               windows_zInfo_mean),
                                                                           invert_where_clause="")

            # Process: Copy Features (Copy Features) (management)
            windowVerticesMaxZ = arcpy.management.CopyFeatures(in_features=windows_zInfo_select, config_keyword="",
                                                               spatial_grid_1=None, spatial_grid_2=None,
                                                               spatial_grid_3=None)

            # Process: Select Layer By Attribute (4) (Select Layer By Attribute) (management)
            # In case there are more than two vertices of the highest Z value -> select only two of them.
            windowVerticesMaxZ_select = arcpy.management.SelectLayerByAttribute(in_layer_or_view=windowVerticesMaxZ,
                                                                                selection_type="NEW_SELECTION",
                                                                                where_clause="OBJECTID = 1 Or "
                                                                                             "OBJECTID = 2",
                                                                                invert_where_clause="")

            # Process: Copy Features (2) (Copy Features) (management)
            windowVerticesMaxZ_twoP = arcpy.management.CopyFeatures(in_features=windowVerticesMaxZ_select,
                                                                    config_keyword="", spatial_grid_1=None,
                                                                    spatial_grid_2=None, spatial_grid_3=None)

            # Process: Near 3D (Near 3D) (3d)
            # Calculate angle between the two vertices
            windowAngle = arcpy.ddd.Near3D(in_features=windowVerticesMaxZ_twoP, near_features=[windowVerticesMaxZ_twoP],
                                           search_radius="", location="NO_LOCATION", angle="ANGLE", delta="NO_DELTA")[0]

            # Process: Add Field (Add Field) (management)
            # Add a field for the search direction values (degrees)
            windowSearchDir = \
                arcpy.management.AddField(in_table=windowAngle, field_name="Search_Direction",
                                          field_type="DOUBLE", field_precision=None, field_scale=None,
                                          field_length=None,
                                          field_alias="Search_Direction", field_is_nullable="NULLABLE",
                                          field_is_required="NON_REQUIRED", field_domain="")[0]

            # Process: Calculate Field (5) (Calculate Field) (management)
            # Change the angle-value of the direction between the two vertices to the same as default in ArcGIS Pro -
            # North is -90 degrees, east is +- 180 degrees, south is 90, west is 0.
            windowSearchDir2 = \
                arcpy.management.CalculateField(in_table=windowSearchDir, field="Search_Direction",
                                                expression="Opposite(!NEAR_ANG_H!)", expression_type="PYTHON3",
                                                code_block="""def Opposite(NEAR_ANG_H):
                if (NEAR_ANG_H <= 0):
                    return NEAR_ANG_H + 90
                elif (NEAR_ANG_H >= 90):
                    return -180 + NEAR_ANG_H -90
                elif (NEAR_ANG_H > 0):
                    return NEAR_ANG_H + 90
            """, field_type="TEXT")[0]

            # Process: Select Layer By Attribute (6) (Select Layer By Attribute) (management)
            # Select only one of the window vertices
            windowSearchDir2_select = arcpy.management.SelectLayerByAttribute(in_layer_or_view=windowSearchDir2,
                                                                              selection_type="NEW_SELECTION",
                                                                              where_clause="OBJECTID = 1",
                                                                              invert_where_clause="")

            # Process: Select Layer By Attribute (7) (Select Layer By Attribute) (management)
            # Select only one of the window vertices
            windowSearchDir2_select2 = arcpy.management.SelectLayerByAttribute(in_layer_or_view=windowSearchDir2,
                                                                               selection_type="NEW_SELECTION",
                                                                               where_clause="OBJECTID = 2",
                                                                               invert_where_clause="")

            # Process: Copy Features (3) (Copy Features) (management)
            windowSearchDir2_select_copy = arcpy.management.CopyFeatures(in_features=windowSearchDir2_select,
                                                                         config_keyword="", spatial_grid_1=None,
                                                                         spatial_grid_2=None, spatial_grid_3=None)

            # Process: Copy Features (4) (Copy Features) (management)
            windowSearchDir2_select2_copy = arcpy.management.CopyFeatures(in_features=windowSearchDir2_select2,
                                                                          config_keyword="", spatial_grid_1=None,
                                                                          spatial_grid_2=None, spatial_grid_3=None)

            # Process: Alter Field (3) (Alter Field) (management)
            # In this and the next process I am changing the search direction field to search direction "high" and "low"
            # These fields will have new values that will be used in the search direction calculation
            windowSearchDir2_select_copy_alter = \
                arcpy.management.AlterField(in_table=windowSearchDir2_select_copy, field="Search_Direction",
                                            new_field_name="Search_dir_low", new_field_alias="Search_dir_low",
                                            field_type="", field_length=8, clear_field_alias="DO_NOT_CLEAR")[0]

            # Process: Alter Field (4) (Alter Field) (management)
            windowSearchDir2_select2_copy_alter = \
                arcpy.management.AlterField(in_table=windowSearchDir2_select2_copy, field="Search_Direction",
                                            new_field_name="Search_dir_high", new_field_alias="Search_dir_high",
                                            field_type="", field_length=8, clear_field_alias="DO_NOT_CLEAR")[0]

            # ### ----------- end of group ----------- ###

            ### Find obstruction angle points within the search direction (parallel to window) ###
            # Process: Near (Near) (analysis)
            # Run the near tool (angle) from all the obstruction points to the window midpoints
            windowToObstructionAngle = arcpy.analysis.Near(in_features=highPointsAddField,
                                                           near_features=[windows_centroid_points],
                                                           search_radius="", location="NO_LOCATION", angle="ANGLE",
                                                           method="PLANAR", field_names=[["NEAR_ANGLE", "NEAR_ANGLE"]])[
                0]

            # Process: Join Field (Join Field) (management)
            # Join the obstruciton points (with an angle to the window midpoint) with the table of one of the window
            # vertices (search direction low)
            angleJoinField = arcpy.management.JoinField(in_data=windowToObstructionAngle, in_field="w_id",
                                                        join_table=windowSearchDir2_select_copy_alter,
                                                        join_field="w_id", fields=["Search_dir_low"])[0]

            # Process: Join Field (2) (Join Field) (management)
            # Same as the one above, just search direction high
            angleJoinField2 = arcpy.management.JoinField(in_data=angleJoinField, in_field="w_id",
                                                         join_table=windowSearchDir2_select2_copy_alter,
                                                         join_field="w_id", fields=["Search_dir_high"])[0]

            # Process: Select Layer By Attribute (5) (Select Layer By Attribute) (management)
            # Select the obstruction points that are within the search direction of the window. These are points that
            # have "opposite" angles of the window. In addition there is a +- 5 degree "buffer" added, to include
            # obstruction points that are almost perpendicular to the window. As an example, if the two window vertices
            # (corners) have the nagle of 90 and -90 degrees between each other (north and south), then this process
            # will look for obstruction points between 0 (+- 5 degrees) and 180 (+- 5 degrees).
            perpendicular_points = arcpy.management.SelectLayerByAttribute(in_layer_or_view=angleJoinField2,
                                                                           selection_type="NEW_SELECTION",
                                                                           where_clause="(NEAR_ANGLE >= ("
                                                                                        "Search_dir_low - 5) And "
                                                                                        "NEAR_ANGLE <= ("
                                                                                        "Search_dir_low + 5)) Or ("
                                                                                        "NEAR_ANGLE >= ("
                                                                                        "Search_dir_high - 5) And ("
                                                                                        "NEAR_ANGLE <= "
                                                                                        "Search_dir_high + 5))",
                                                                           invert_where_clause="NON_INVERT")

            # Process: Copy Features (6) (Copy Features) (management)
            perpendicular_points_copy = arcpy.management.CopyFeatures(in_features=perpendicular_points,
                                                                      config_keyword="", spatial_grid_1=None,
                                                                      spatial_grid_2=None, spatial_grid_3=None)

            # Process: Calculate Field (4) (Calculate Field) (management)
            # Calculating the OA for the window
            # grid_code = Height of the obstruction point
            # Z_mean = The height of the window midpoint
            # Distance = The distance from the window midpoint to the obstruction point in 2D (meaning height
            # differences are not included)
            # highPoints_all_values =
            OA_calc = arcpy.management.CalculateField(in_table=perpendicular_points_copy, field="OA",
                                                      expression="math.degrees(math.atan(("
                                                                 "!grid_code!-!Z_Mean!)/(!Distance!)))",
                                                      expression_type="PYTHON3", code_block="",
                                                      field_type="TEXT")[0]

            # Process: Select Layer By Attribute (Select Layer By Attribute) (management)
            # Only select the obstruction point with the highest value
            windows_OA_field = ['OA']
            OAValues = []
            with arcpy.da.SearchCursor(OA_calc, windows_OA_field) as cursor4:
                for r4 in cursor4:
                    OAValues.append(float(r4[0]))

            # In case there are no obstruction points - take the window midpoint and set the OA value to 0
            if len(OAValues) == 0:
                NoOutputSelect = arcpy.management.SelectLayerByAttribute(in_layer_or_view=angleJoinField2,
                                                                         selection_type="NEW_SELECTION",
                                                                         where_clause="OBJECTID = 1",
                                                                         invert_where_clause="")

                NoOutputCopy = arcpy.management.CopyFeatures(in_features=NoOutputSelect,
                                                             config_keyword="", spatial_grid_1=None,
                                                             spatial_grid_2=None, spatial_grid_3=None)

                NoOAOutput = arcpy.management.CalculateField(in_table=NoOutputCopy,
                                                             field="OA", expression="0",
                                                             expression_type="PYTHON3",
                                                             code_block="", field_type="TEXT")[0]

                windowOutputData.append(NoOAOutput)

            # If there are obstruction points, set it to the highest value (max)
            else:
                maxOAValue = max(OAValues)

                perpendicular_points_select = arcpy.management.SelectLayerByAttribute(
                    in_layer_or_view=perpendicular_points_copy,
                    selection_type="NEW_SELECTION",
                    where_clause="OA = {}".format(maxOAValue), invert_where_clause="")

                # Process: Copy Features (5) (Copy Features) (management)
                perpendicular_points_copy2 = arcpy.management.CopyFeatures(in_features=perpendicular_points_select,
                                                                           config_keyword="", spatial_grid_1=None,
                                                                           spatial_grid_2=None, spatial_grid_3=None)
                # ### ----------- end of group ----------- ###

                # Add the layer including the max obstruction point of a window to a list
                windowOutputData.append(perpendicular_points_copy2)

            windowID += 1  # Increment the window ID, so the next window will have another ID value.

    arcpy.AddMessage("Merging data before returning results...")
    # Process: Merge (Merge) (management)
    # Merge all the windows in the list, after all input windows have been visited.
    mergedWindowData = arcpy.management.Merge(inputs=windowOutputData, add_source="NO_SOURCE_INFO")

    # Process: XY Table To Point (3) (XY Table To Point) (management)
    # Output point at the location of each window, for visualization and to access the table.
    outputWindowPoints = arcpy.management.XYTableToPoint(in_table=mergedWindowData, out_feature_class=outputPath,
                                                         x_field="cent_long_x", y_field="cent_lat_y", z_field="Z_Mean",
                                                         coordinate_system=spatial_ref)


# Inputs from the user
windows = arcpy.GetParameterAsText(0)
DSM = arcpy.GetParameterAsText(1)
outputPath = arcpy.GetParameterAsText(2)

# argv creates a a list of strings representing the arguments. argv[0] is the file name, we do not need this, so we
# start from [1].
if __name__ == '__main__':
    OAcalc(*argv[1:])
