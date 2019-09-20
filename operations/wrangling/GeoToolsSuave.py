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
            return ql.slider(updated_df)
        
        if geo_button.value == True:
            # Temporarily disables geocode button
            geo_button.disabled = True
            geo_button.value = False
            return 'Geocoding in progress. Please wait..'
    
        # Checks for existing latitude/longitude columns
        for col in updated_df.columns:
            if '#number#hidden' in col:
                error = '#####Coordinate columns already exist.'
                return pn.Column(error, slider(updated_df))
        
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

        row_slider = ql.slider(updated_df)
        
        return row_slider

    geo_widgets = pn.Row(geo_select, geo_button, margin=(0,0,15,0))
    widgets = pn.Column(geo_widgets, geocode_trigger)
    
    return widgets


def get_coords(address):
    """
    get_coords uses the data science tool kit to geocode
    addresses.
    
    :param address: string representing location
    :returns: dictionary with keys as addresses and
              values as latitude/longitude coordinates
    """
    
    if pd.isnull(address):
        return 
    
    # dstk API url
    partial_url = "http://www.datasciencetoolkit.org/maps/api/geocode/json?sensor=false&address="
    
    # Reformats string to work with dstk API
    address_reformat = address.replace(" ", "+").replace("'", "")
    
    # Geocodes address
    response = requests.get(partial_url+address_reformat).json()
    
    # Handles case of no results/invalid address
    if response['status'] == 'ZERO_RESULTS':
        return {address: [None, None]}
    
    # Extracts result
    coords = response['results'][0]['geometry']['location']
    lat = coords['lat']
    lon = coords['lng']
    
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
    generator = pn.widgets.Toggle(name='Generate Geometry', disabled=True, margin=(20,0,0,30), width=200)

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

        generator.disabled = False

        return pn.pane.Markdown(response, margin=(5,10,5,10), width=625)

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
            if pd.isnull(string):
                return None
            elif string.lower() in geometries.keys():
                return geometries[string.lower()]
            else:
                return ''

        if generate:
            df['geometry'] = df[column_selector.value].apply(geom_function)
            generator.disabled = True
            return ql.slider(df)    

    # Display widgets
    selectors = pn.Row(column_selector, prop_selector)
    selectors_display = pn.Column(selectors, display_match, css_classes=['widget-box'])
    top_panel = pn.Row(selectors_display, generator)
    geom_df = pn.Row(generate_geometry, margin=(20,0,0,0))
    geom_display = pn.Column(top_panel, geom_df)
    
    return geom_display
    