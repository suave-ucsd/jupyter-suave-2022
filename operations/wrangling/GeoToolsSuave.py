""" Geocoder and Geometry Generator

This script has two main functions: geocode columns from a
pandas data frame and produce a geometry column in WKT format
from a GeoJSON file.

To achieve this functionality simply run geocoder() and 
json_to_geometry() respectively.

QualifierSuave must be in the same directory and run prior to
running this script. Please refer to QualifierSuave for information
on running it.

This script requires that requests, pandas, json, and panel 
be installed within the Python environment you are running 
this script on.
"""


# Importing required scripts
import QualifierSuave as ql

# Importing libraries
import requests
import pandas as pd
import json
import panel as pn

import sys
sys.path.insert(1, '../../helpers')
import panel_libs as panellibs


# Loading extensions
pn.extension()


def geocoder(options):
    """
    geocoder allows users to select a column to geocode
    and produce latitude/longitude columns for those
    respective locations.
    
    :param options: Array of columns that can be geocoded
    :returns: widgets to select column to geocode
    """
    # Geocode Column Selector widget
    geo_options = ['None'] + list(pd.Series(options).unique())
    geo_select = pn.widgets.Select(name='Select Column to Geocode', options=geo_options, width=200)

    # Geocode Button widget
    geo_button = pn.widgets.Toggle(name='Geocode', margin=(15,0,0,30), width=200)
    
    # Progress widget
    global progress_geocode
    progress_geocode = pn.pane.Markdown('')
    
    # Stores geocoded and non-geocoded values
    global is_geocoded
    global not_geocoded
    is_geocoded = []
    not_geocoded = []

    @pn.depends(geo_button.param.value)
    def geocode_trigger(click):
        """
        geocode_trigger initializes geocoding when the 
        geocode button widget is selected.
    
        :param click: bool indicated click on geocode button widget
        :returns: updated data frame with latitude and longitude columns
        """
        
        updated_df = ql.updated_df
        
        if geo_select.value == 'None':
            geo_button.value = False
            return panellibs.slider(updated_df)
        
        if geo_button.value == True:
            # Temporarily disables geocode button
            geo_button.disabled = True
            geo_button.value = False
            return 'Geocoding in progress. Please wait..'
    
        # Checks for existing latitude/longitude columns
        for col in updated_df.columns:
            if '#number#hidden' in col:
                error = '#####Coordinate columns already exist.'
                return pn.Column(error, panellibs.slider(updated_df))
        
        # Geocodes and stores latitude/longitude for each address
        unique_vals = updated_df[geo_select.value].dropna().unique()
        coords = pd.Series(unique_vals).apply(get_coords)
        
        address_dict = {}
        coords.apply(lambda address: address_dict.update(address))
        
        # Creating latitude/longitude columns
        updated_df['latitude#number#hidden'] = (updated_df[geo_select.value]
                                                .map(address_dict)
                                                .apply(lambda x: x[0] if type(x) == list else None))
        updated_df['longitude#number#hidden'] = (updated_df[geo_select.value]
                                                 .map(address_dict)
                                                 .apply(lambda x: x[1] if type(x) == list else None))

        progress_geocode.object = ''
        
        report_message = pn.pane.Markdown('**Geocoding Finished:**', margin=(24,20,0,0))
        geocoded_vals = pn.widgets.Select(name='Geocoded Values', options=is_geocoded, width=200)
        non_geocoded_vals = pn.widgets.Select(name='Non Geocoded Values', options=not_geocoded, width=200)
        full_report = pn.Row(report_message, geocoded_vals, non_geocoded_vals, margin=(5,0,20,0))
                        
        row_slider = panellibs.slider(updated_df)
        full_display = pn.Column(full_report, row_slider)

        return full_display

    geo_widgets = pn.Row(geo_select, geo_button, margin=(0,0,15,0))
    widgets = pn.Column(geo_widgets, geocode_trigger, progress_geocode)
    
    return widgets


def get_coords(address):
    """
    get_coords uses the data science tool kit to geocode
    addresses.
    
    :param address: string representing location
    :returns: dictionary with keys as addresses and
              values as latitude/longitude coordinates
    """
        
    # Base progress menu for geocoder
    base_progress = ('| Placename | Status | Latitude | Longitude |' + 
                     '\n|:---------:|:-------:|:--------:|:---------:|')
    
    if pd.isnull(address):
        progress_geocode.object = base_progress + '\n| Null | Failed | Null | Null |'
        return 
    
    # dstk API url
    partial_url = "http://www.datasciencetoolkit.org/maps/api/geocode/json?sensor=false&address="
    
    # Reformats string to work with dstk API
    address_reformat = address.replace(" ", "+").replace("'", "")
    
    # Geocodes address
    response = requests.get(partial_url+address_reformat).json()
    
    # Handles case of no results/invalid address
    if response['status'] == 'ZERO_RESULTS':
        not_geocoded.append(address)
        progress_geocode.object = base_progress + '\n| ' + address + ' | Failed | Null | Null |'
        return {address: [None, None]}
    
    # Extracts result
    coords = response['results'][0]['geometry']['location']
    lat = coords['lat']
    lon = coords['lng']
    
    progress_geocode.object = base_progress + ('\n| ' + address + ' | Geocoded | ' + 
                                               str(lat) + ' | ' + str(lon) + ' |')
    
    is_geocoded.append(address)
    
    return {address: [lat, lon]}


def json_to_geometry(file_value, options):
    """
    json_to_geometry parses a GeoJSON file to match
    to a user selected column's values so that geometry 
    can be generated for each value if it exists.
    
    :param file_value: contents of a GeoJSON file
    :param options: Array containing possible options to
                    match to the GeoJSON file
    :returns: widgets to select column to match and initiate
              process
    """
    
    # Column Selector widget
    column_selector = pn.widgets.Select(name='Select Column to Match', options=['None']+options)

    # Geojson Property Selector widget
    json_props = list(json.loads(file_value)['features'][0]['properties'].keys())
    prop_selector = pn.widgets.Select(name='Select GeoJSON Property to Match', options=['None']+json_props)

    # Geometry Generator button
    generator = pn.widgets.Toggle(name='Generate Geometry', disabled=True, margin=(22,0,0,30), width=200)
    
    # Progress widget for json to geometry
    global progress_json
    progress_json = pn.pane.Markdown('', margin=(-20,0,0,0))
    
    # Stores values that produced/did not produce geometries
    with_geom = []
    no_geom = []

    df = ql.updated_df
    geometries = {}

    @pn.depends(column_selector.param.value, prop_selector.param.value)
    def display_match(col, prop):
        """
        display_match parses through a GeoJSON file's properties
        (as selected by the user) to determine the number of values
        in a data frame that have an available geometry.

        :param col: Series containing values to seach in GeoJSON
        :param prop: String representing property in GeoJSON where
                     match should be searched for
        :returns: widgets and match results
        """

        if (col == 'None') or (prop == 'None'):
            return

        # Extracts all property values from json and geometries for future use
        prop_vals = []

        for feature in json.loads(file_value)['features']:
            geometry = feature['geometry']

            # Ensures feature has a geometry
            if len(geometry['coordinates']) > 0:

                # Stores property value
                properties = feature['properties']
                prop_val = properties[prop]
                prop_vals.append(prop_val.lower())

                # Stores geometries in WKT format
                geom_type = geometry['type'].upper()
                cleaned_coords = (str(geometry['coordinates'])[1:-1]
                                  .replace(',', ' ').replace('  ', ' ')
                                  .replace('] [', ', ').replace(']  [', ', ')
                                  .replace('[','(').replace(']',')'))
                geometries[prop_val.lower()] = geom_type+' '+cleaned_coords

        # Determines which column values are existing property values
        col_vals = list(df[col].str.lower().unique())

        valid_col_vals = []
        for col_val in col_vals:
            if col_val in prop_vals:
                valid_col_vals.append(col_val)

        # Determines number of column values that are a match
        value_counts = df[col].str.lower().value_counts()

        match = 0
        for col_name in valid_col_vals:
            match += value_counts[col_name]

        # Formualtes response for user
        response = ("**"+str(match)+"** of **"+str(len(df))+
                    "** values in '"+col+"' have a geometry. "+
                    "Please click on 'Generate Geometry' to continue.")
        
        global response_widget
        response_widget = pn.pane.Markdown(response, margin=(5,10,5,10), width=625)

        generator.disabled = False

        return response_widget

    @pn.depends(generator.param.value)
    def generate_geometry(generate):
        """
        generate_geometry produces a data frame
        with an added geometry column for values
        in a predefined column in that same data frame.

        :param generate: bool indicated click on generate button widget
        """

        def geom_function(string):
            """
            geom_function checks if a string is a 
            key in the global dictionary 'geometries'
            and outputs its value if true.

            :param string: String to be check in dictionary
            """
            
            # Base progress menu for json to geometry
            base_progress = ('| Placename | Status |' + 
                             '\n|:---------:|:-------:|')
            
            if pd.isnull(string):
                progress_json.object = base_progress + '\n|  Null  | Failed |'
                return None
            elif string.lower() in geometries.keys():
                progress_json.object = base_progress + '\n| ' + string + ' | Success |'
                with_geom.append(string)
                return geometries[string.lower()]
            else:
                progress_json.object = base_progress + '\n| ' + string + ' | Failed |'
                no_geom.append(string)
                return ''

        if generate:
            
            generator.disabled = True
            response_widget.object = ''
            
            # checks for existing geometry column
            for col in df.columns:
                if 'geometry' in col.lower():
                    generator.disabled = True
                    message = pn.pane.Markdown('Geometry column already exists. Either remove ' + 
                                               'column above or continue.', margin=(-25,0,15,0))
                    return pn.Column(message, panellibs.slider(df))
            
            # Generates geometries
            unique_vals = df[column_selector.value].unique()
            geometry_vals = pd.Series(unique_vals).apply(geom_function)
            geom_dict = pd.Series(geometry_vals.values, index=unique_vals).to_dict()
            df['geometry#hiddenmore'] = df[column_selector.value].map(geom_dict)
            
            progress_json.object = ''
            
            # Produce final widgets
            report_message = pn.pane.Markdown('**Geometries Generated:**', margin=(24,20,0,0))
            geom_vals = pn.widgets.Select(name='With Geometry', options=with_geom, width=200)
            non_geom_vals = pn.widgets.Select(name='No Geometry', options=no_geom, width=200)
            full_report = pn.Row(report_message, geom_vals, non_geom_vals, margin=(-20,0,20,0))
                        
            row_slider = panellibs.slider(df)
            full_display = pn.Column(full_report, row_slider)
            
            return full_display   

    # Display widgets
    selectors = pn.Row(column_selector, prop_selector, margin=(2,2,2,5))
    selector_panel = pn.Row(selectors, css_classes=['widget-box'])
    left_panel = pn.Column(selector_panel, display_match)
    top_panel = pn.Row(left_panel, generator)
    geom_df = pn.Column(progress_json, generate_geometry, margin=(20,0,0,0))
    geom_display = pn.Column(top_panel, geom_df)
    
    return geom_display
    