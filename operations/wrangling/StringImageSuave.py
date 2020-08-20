# Importing libraries
from PIL import Image, ImageDraw, ImageFont
import os
import re
import pandas as pd
import shutil
import glob
import panel as pn

# Importing required scripts
import QualifierSuave as ql

# Loading extensions
pn.extension()

import sys
sys.path.insert(1, '../../helpers')
import panel_libs as panellibs



# Variable to prevent multiple runs of this script
run = False

def image_display(df, cols, url):
    
    # Column Selector widget
    col_options = cols
    selector_name = 'Select Images Column'
    col_selector = pn.widgets.Select(name=selector_name, options=col_options, width=200)
    
    # Image generation button
    generator = pn.widgets.Toggle(name='Generate Images', margin=(15,20,0,30), width=200)
    
    # Progress widget for image generation
    global progress_img
    progress_img = pn.pane.Markdown('')
    
    @pn.depends(generator.param.value)
    def generate_trigger(click):
        
        global run
        
        if (generator.value == False) and (not run):
            display = pn.Row(panellibs.slider(ql.updated_df), margin=(20,0,0,-220))
            return display
        
        if run and not click:
            global image_df
            image_df = generate_images(df, col_selector.value)
            
            progress_img.object = ''
            message = pn.pane.HTML("<p>Done. Zip archive with images " +
                                   "ready to download <a href='" + url + "/generated_images.zip'" + 
                                   " target='_blank'>here</a>.</p>")
            display = pn.Row(panellibs.slider(ql.updated_df), margin=(20,0,0,-220))
            
            return pn.Column(message, display)
            
        
        elif click:
            run = True
            generator.value = False
            generator.disabled = True
            
            return 'Images are being created. Please wait..'

    # Display widgets
    right_panel = pn.Column(generator, generate_trigger)
    options = pn.Row(col_selector, right_panel)
    widgets = pn.Column(options, progress_img)
    
    return widgets

# Base progress menu for image generation
base_progress = ('| Value | Status |' + 
                 '\n|:---------:|:-------:|')


def generate_images(nonimage_df, col):
    
    nonimage_df.to_csv('images/string_image_df.csv')
    
    input_file = 'string_image_df.csv'
    outcsv = input_file[0:-4] + '_img.csv'
    column_to_convert = col

    if os.path.isdir("images"):
        os.chdir("images")
    else:
        os.mkdir("images")
        os.chdir("images")
    
    if 'Unnamed: 0' in nonimage_df.columns:
        df = pd.read_csv(input_file, encoding = "utf-8").drop('Unnamed: 0', axis=1)
    else:
        df = pd.read_csv(input_file, encoding = "utf-8")

    df.fillna('', inplace=True)
    df["#img"] = ''

    for index, row in df.iterrows():
        if row[column_to_convert] == '':
            row["#img"] = "image_not_available"
            progress_img.object = base_progress + '\n| ' + row[column_to_convert] + ' | Image Not Available |'
        elif 'field_or_processed' not in row.index:
            fname = to_image(row[column_to_convert],"white","blue","_o")
            row["#img"] = fname
        else:
        
#         additional conditions:
            if row['field_or_processed'] == "Processed Data":
                fname = to_image(row[column_to_convert],"orange","blue","_p")
            elif row['field_or_processed'] == "Field Data":
                fname = to_image(row[column_to_convert],"green","yellow","_f")
            else:
                fname = to_image(row[column_to_convert],"white","blue","_o")
            row["#img"] = fname

    # Moves arial.ttf to working directory
    os.chdir("..")
    os.rename("images/arial.ttf", "arial.ttf")
    os.remove("images/string_image_df.csv")

    # Zips and removes files
    shutil.make_archive('generated_images', 'zip', 'images')

    files = glob.glob('images/*')
    for f in files:
        os.remove(f)

    # Moves arial.ttf back to images folder
    os.rename("arial.ttf", "images/arial.ttf")
    
    return df


def to_image(unicode_text, bgr_color, text_color,colortype):
    
    progress_img.object = base_progress + '\n| ' + unicode_text + ' | Image Generated |'
    
    filename = re.sub(r'[\\\\/*?:"<>|]',"",unicode_text)
    filename = filename.replace(" ", "_")
    filename = filename.replace(".", "_")
    
    font = ImageFont.truetype("arial.ttf", 28, encoding="unic")
    text_width, text_height = font.getsize(unicode_text)

    if text_width *1.0 / text_height > 1.5:
        text_height = int(text_width/1.5)
        text_y = int(text_height/2.0) - 10
        text_x = 5
    else:
        text_width = int(text_height*1.5)
        text_y = 2
        text_x = int(text_width/2.0) -5

    canvas = Image.new('RGB', (text_width + 10, text_height + 10), bgr_color)
    draw = ImageDraw.Draw(canvas)
    draw.text((text_x, text_y), unicode_text, text_color, font)
    canvas.save(filename + colortype + ".png", "PNG")
    
    return filename+colortype
