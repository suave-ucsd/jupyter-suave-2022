""" Data Display & Editor

This script reads in a file from your directory (.tsv, .txt, .csv)
and displays its contents to the user. Users can then select and 
modify the file through the use of widgets.

To achieve this functionality, simply run view_data() by 
providing it with a valid path to the file.

This script requires that pandas and panel be installed 
within the Python environment you are running this script on.
"""


# Importing libraries
import pandas as pd
import panel as pn

# Loading extensions
pn.extension()


def view_data(path):
    """
    Main function

    view_data displays all necessary widgets to view, 
    modify, and save a file from a file path.

    :param link: string representing path to file
    :returns: data frame with editor widgets
    """
            
    # Reads in data 
    data = extract_data(path)
    
    # Row Selector widget
    row_selection = pn.widgets.IntSlider(name='Navigate Rows', 
                                         width=350, margin=(0,50,-15,0))

    # Column Selector widget
    col_selection = pn.widgets.IntSlider(name='Navigate Columns', 
                                         width=350, margin=(0,0,5,0))

    # Radio Selector widget + Text
    radio_text = pn.Row('##### Select Columns/Rows to Drop', margin=(0,0,-15,115))
    radio_selection = pn.widgets.RadioButtonGroup(options=['Rows', 'Columns'], 
                                                  value='Columns', width=398)

    # Column Drop Selector widget
    col_drop = pn.widgets.Select(width=180, margin=(15,0,0,0))

    # Row Drop Input widget
    row_drop = pn.widgets.TextInput(placeholder='Number/Range(e.g. 1-5)', 
                                    width=170, margin=(10,23,10,20))
    
    # Drop Button widget
    dropper = pn.widgets.Toggle(name='Drop', width=250, margin=(5,10,10,80))

    # Header Selector widget
    head_options = list(range(1,5))
    head_selection = pn.widgets.Select(name="Select Number of Headers", width=230, 
                                       options=head_options, value=1, margin=(12,10,10,10))

    # Undo Button widget
    undo = pn.widgets.Toggle(name='Undo', margin=(25,0,0,55), width=200)
    
    # Save widget
    saver = pn.widgets.Toggle(name='Finish & Save Data', button_type='danger', 
                              margin=(10, 0, 0, 55), width=200)
   
    # Keeps track of last change to data frame in case of an undo
    global header_vals
    global change
    header_vals = []
    change = ''
    
    # Variables that help detect changes in headers
    global started
    global head_val
    head_val = 1
    started = False

    @pn.depends(row_selection.param.value, col_selection.param.value, 
                radio_selection.param.value, dropper.param.value, 
                head_selection.param.value, undo.param.value, saver.param.value)
    def select_data(row, col, radio, drop, head, back, save):
        """
        select_data updates the existing data frame 
        and/or other widgets when there are changes 
        to a particular widget.

        :param row: integer representing number of rows to show
        :param col: integer representing number of columns to show
        :param radio: string representing whether to drop columns/rows
        :param drop: bool indicating whether to drop columns/rows
        :param head: integer representing number of headers
        :param back: bool indicating whether to undo changes
        :param save: bool indicating click on saver widget
        :returns: updated data frame
        """
        
        # Please note: Any function that is dependent on a widgets value 
        # (@pn.depends), like this one, will run every time one of the widget's
        # value is changed. However, this is not limited to a user changing the
        # widgets, but also changed programmatically as well. This is done a
        # few times across this function which leads to redundant calls.
        # These redundant calls can cause problems as they can reassign variables.
        # Hence, you may see some extra variables to detect these redundant calls
        # such as 'started' or 'head_val' to detect a change in the header selector.

        # Checks for previous run of this function or change in data
        global active_data
        global updated_df
        global stored_data
        global previous_stored
        global previous_df
        global change
        global started
        global head_val
        
        if ('updated_df' in globals()) and (path == active_data):
            df = updated_df.copy()
        else:
            active_data = path
            #df = data
            df = extract_data(path)
            stored_data = df.copy()
            previous_stored = stored_data.copy()
            previous_df = df.copy()
            updated_df = df.copy()
        
        # Checks for click on the undo button
        if back:
            undo.value = False
            
            if change == '':
                return updated_df.iloc[row:row+6, col:col+13]
            
            elif change == 'header':
                change = 'skip'
                if len(header_vals) > 1:
                    head_selection.value = header_vals[-2]
                else:
                    head_selection.value = header_vals[0]
                
            elif change == 'axis':
                stored_data = previous_stored.copy()
            
            change = ''
            updated_df = previous_df.copy()
            
            return updated_df.iloc[row:row+6, col:col+13]

        # Instantiates data and enables widgets
        if radio == 'Columns':
            row_drop.disabled = True
            col_drop.disabled = False
        else:
            col_drop.disabled = True
            row_drop.disabled = False
        row_selection.start, row_selection.end = 0, len(df) - 1
        col_selection.start, col_selection.end = 0, len(df.columns)

        # Combines header rows and creates data frame with appropriate header
        # Checks to see if header value changed
        if ((head != head_val) or not started) and (change != 'skip'):
            # Stores head values in case an undo is selected
            change = 'header'
            header_vals.append(head)
            
            head_rows = stored_data.iloc[0:head-1].T.reset_index().fillna('')
            columns = head_rows.apply(lambda row: ' '.join(row.values.astype(str)), axis=1)

            updated_df = stored_data.copy()
            updated_df.columns = columns
            updated_df = updated_df.iloc[head-1:]
            
            started = True
            head_val = head
            
        col_drop.options = list(updated_df.columns)

        # Updates data frame when column/row is dropped
        if drop:
            if (row_drop.value == '') and (radio == 'Rows'):
                dropper.value = False
                return updated_df.iloc[row:row+6, col:col+13]
            
            change = 'axis'
            dropper.value = False
            if radio == 'Columns':
                previous_df = updated_df.copy()
                col_index = updated_df.columns.get_loc(col_drop.value)
                updated_df = updated_df.drop(col_drop.value, axis=1)
                previous_stored = stored_data.copy()
                stored_data = stored_data.drop(stored_data.columns[col_index], axis=1)
                dropper.value = False
            else:
                poss_values = [str(x) for x in list(df.index)]
                
                # Checks for range of values
                if '-' in row_drop.value:
                    num_list = row_drop.value.split('-')
                    lower = num_list[0]
                    upper = num_list[1]
                    
                    for bound in [lower, upper]:
                        # Checks for invalid row number
                        if (not bound.isdigit()) or (bound not in poss_values):
                            dropper.value = False
                            return updated_df.iloc[row:row+6, col:col+13]
                    
                    # Removes range of values
                    previous_df = updated_df.copy()
                    lower_frame = updated_df[updated_df.index < int(lower)]
                    upper_frame = updated_df[updated_df.index > int(upper)]
                    updated_df = pd.concat([lower_frame, upper_frame])
                    previous_stored = stored_data.copy()
                    stored_lower_frame = stored_data[stored_data.index < int(lower)]
                    stored_upper_frame = stored_data[stored_data.index > int(upper)]
                    stored_data = pd.concat([stored_lower_frame, stored_upper_frame])
                    row_drop.value = ''
                  
                else:    
                    # Checks for invalid row number
                    if (not row_drop.value.isdigit()) or (row_drop.value not in poss_values):
                        dropper.value = False
                        return updated_df.iloc[row:row+6, col:col+13]

                    previous_df = updated_df.copy()
                    updated_df = updated_df.drop(int(row_drop.value))
                    previous_stored = stored_data.copy()
                    stored_data = stored_data.drop(int(row_drop.value))
                    row_drop.value = ''

        # Saves data frame when user clicks save widget
        if save:
            global final_df
            final_df = updated_df.reset_index(drop=True)
            saver.value = False

        return updated_df.iloc[row:row+6, col:col+13]

    # Displays widgets
    navigators = pn.Row(row_selection, col_selection , margin=(30,0,0,10))
    drop_options = pn.Row(row_drop, col_drop)
    drop_widgets = pn.Column(pn.Column(radio_text, radio_selection), 
                             drop_options, dropper, width=420, 
                             css_classes=['widget-box'])
    header = pn.Column(head_selection, margin=(0,0,0,30), 
                       width=250,css_classes=['widget-box'])
    right_panel = pn.Column(header, undo, saver, width = 300)
    editors = pn.Row(drop_widgets, right_panel, margin=(30,0,0,30))
    widgets = pn.Column(navigators, select_data, editors)
    
    return widgets


def extract_data(path):
    """
    Helper function for view_data
    
    extract_data reads files from various formats
    
    :param link: string representing path to file
    :returns: data frame of file
    """

    # Reading file at path
    if path.endswith(('.txt', 'tsv')):
        try:
            data = pd.read_csv(path, sep='\t', encoding="latin-1")
        except UnicodeDecodeError:
            data = pd.read_csv(path, sep='\t', encoding="ISO-8859-1")
    elif path.endswith('.csv'):
        try:
            data = pd.read_csv(path, encoding="latin-1")
        except UnicodeDecodeError:
            data = pd.read_csv(path, encoding="ISO-8859-1")
    else:
        return None
    
    cleaned_data = (data
                    .dropna(axis=1, how='all')
                    .dropna(axis=0, how='all'))
    
    return cleaned_data
