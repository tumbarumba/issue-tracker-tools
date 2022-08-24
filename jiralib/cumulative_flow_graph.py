#!/usr/bin/env python

from matplotlib.lines import Line2D
import matplotlib.pyplot as pyplot
import matplotlib.patches as Patches
import pandas
import os
import sys
import numpy
from datetime import datetime, timedelta
from dateutil.parser import isoparse
from math import ceil

class CumulativeFlowGraph:
    def __init__(self, project_config, csv_file, png_file):
        self.project_config = project_config
        self.today_date = datetime.today().date()
        self.csv_file = csv_file
        self.png_file = png_file

    def run(self, open_graph):
        print(f"Reading cumulative flow data from {str(self.csv_file)}")
        self.build_graph()
        if open_graph:
            os.system(f"xdg-open '{self.png_file}'")

    def build_graph(self):
        self.read_csv_values()
        colours = self.colour_scheme("pastels")
        end_duration, trend_slope, trend_y_intercept = self.calculate_trend_prediction()
        final_x_axis,final_y_axis, predicted_end_date = self.select_final_axis(end_duration)
        legend_elements = self.generate_legend(colours)
        self.write_stacked_area_graph(final_x_axis, final_y_axis, legend_elements,colours)
        self.write_trend_line(final_x_axis, trend_slope, trend_y_intercept, colours)
        self.find_milestone_dates(final_x_axis, predicted_end_date, colours)
        self.save_graph()

    def read_csv_values(self):
        self.df = pandas.read_csv(self.csv_file)
        self.x_axis_data = self.df['date'].tolist()
        self.y_axis_data = [self.df['done'].tolist(), self.df['in_progress'].tolist(), self.df['pending'].tolist()]

    def calculate_trend_prediction(self):
        if len(self.x_axis_data)>14:
            prediction_data = self.df['done'].tolist()[-14:]
        else:
            prediction_data = self.df["done"].tolist()
        trend_slope,trend_y_intercept = numpy.polyfit(range(len(prediction_data)),prediction_data, 1)
        end_duration = (self.df['total'].tolist()[-1]-trend_y_intercept)/trend_slope
        return(end_duration, trend_slope, trend_y_intercept) 

    def select_final_axis(self, end_duration):
        final_milestone = self.project_config.milestones[-1]["date"]
        if len(self.x_axis_data)>14:
            start_index = len(self.x_axis_data)-14
        else:
            start_index = 0
        start = isoparse(self.x_axis_data[start_index]).date()
        predicted_end_date = start + timedelta(days = ceil(end_duration))
        if (predicted_end_date - final_milestone).days <15:
            #if final milestone and predicted finish are relatively close show both
            end = max(predicted_end_date, final_milestone) +timedelta(days=2)
        else:
            end = final_milestone +timedelta(days = 15)
        
        generated_dates = pandas.date_range(start, end).date
        final_x_axis = [str(date) for date in generated_dates]
        end_index = start_index + len(final_x_axis)
        final_y_axis = []
        
        for i in range(3):
            data = list(self.y_axis_data[i][start_index:end_index])
            while len(data) < len(final_x_axis):
                data.append(self.y_axis_data[i][-1])
            final_y_axis.append(data)
        return (final_x_axis,final_y_axis, predicted_end_date)

    def generate_legend(self,colours):
        '''generates a list of all the information need to show the legend'''
        legend_elements = [Patches.Patch(facecolor=colours["Pending"], label="Pending"), 
                            Patches.Patch(facecolor=colours["In Progress"], label="In Progress"),
                            Patches.Patch(facecolor=colours["Done"], label="Done"),
                            Line2D([0], [0], color=colours["Current Date"], label="Current Date"),
                            Line2D([0], [0], color=colours["Predicted End Date"], label="Predicted End Date")
                            ] #manual list of stackplot legend elements.
        for i in range(len(self.project_config.milestones)):
            legend_elements.append(Line2D([0], [0], color=colours[self.project_config.milestones[i]['name']], label=self.project_config.milestones[i]['name']))
            #adds milestons elements from conf
        return(legend_elements)   

    def write_stacked_area_graph(self, final_x_axis, final_y_axis, legend_elements,colours):
        '''All formating graph visuals'''
        pyplot.stackplot(final_x_axis, final_y_axis,colors=[colours["Done"],colours["In Progress"],colours["Pending"]])
        pyplot.legend(handles=legend_elements, loc='upper left')
        pyplot.xticks(rotation = 90)
        pyplot.xlabel("Dates", labelpad=12, fontsize=12)
        pyplot.ylabel("Total Stories", labelpad=9,fontsize=12)
        pyplot.title(self.project_config.project_name, pad=9 ,fontsize=16)
        pyplot.gca().margins(0, 0)
        pyplot.gcf().canvas.draw()
        tl = pyplot.gca().get_xticklabels()
        maxsize = max([t.get_window_extent().width for t in tl])
        s = maxsize/pyplot.gcf().dpi*(len(final_x_axis))*2*0.8
        margin = 0.8/pyplot.gcf().get_size_inches()[0]
        pyplot.gcf().subplots_adjust(left=margin, right=1.-margin, bottom=.3)
        pyplot.gcf().set_size_inches(s, pyplot.gcf().get_size_inches()[1]*1.5)     

    def write_trend_line(self,final_x_axis, trend_slope, trend_y_intercept, colours):
        '''Plots linear regression line'''
        left_intercept = trend_y_intercept
        # left_intercept = trend_y_intercept + start_index*trend_slope
        trend_range_of_x_points = range(len(final_x_axis))
        pyplot.plot(trend_range_of_x_points, trend_slope*trend_range_of_x_points + left_intercept, color=colours["Trendline"])
    
    def find_milestone_dates(self,final_x_axis, predicted_end_date, colours):
        '''checks for existence of data + calls writing func'''
        self.write_date_line(final_x_axis.index(str(self.today_date)), colours["Current Date"])
        if self.project_config.milestones is not None:
            for i in range(len(self.project_config.milestones)):
                milestone_date = str(self.project_config.milestones[i]['date'])
                milestone = self.project_config.milestones[i]
                if str(milestone["date"]) in final_x_axis:
                    self.write_date_line(final_x_axis.index(str(milestone["date"])), colours[milestone["name"]])
                else:
                    sys.exit(f'Error: Milestone "{self.project_config.milestones[i]["date"]}" has no date.')
        end_date = str(predicted_end_date)
        self.write_date_line(end_date, colours["Predicted End Date"])

    def write_date_line(self,x_axis_position_index, line_color):
        '''plots date lines'''
        max_total = max(self.df['total'].tolist())
        pyplot.vlines(x_axis_position_index, 0, max_total+(max_total/6), color=line_color)

    def save_graph(self):
        '''saves graph, creates file locations if necessary'''
        if not os.path.isdir(f"reports"):
            os.mkdir("reports")
        if not os.path.isdir(f"reports/{self.project_config.project_name}"):
            os.mkdir(f"reports/{self.project_config.project_name}")
        if os.path.isdir(f"reports/{self.project_config.project_name}"):
            pyplot.savefig(self.png_file)
            print(f"Cumulative flow graph saved as {self.png_file}")

    def colour_scheme(self, theme):
        if theme == "sunset":
            colours = {"Done":"#e76f51",
             "In Progress":"#f4a261",
             "Pending" : "#e9c46a",
             "Current Date":"#A188A6",
             "Predicted End Date": "#788AA3",
             "Iteration 3 Demo": "indigo",
             "Trendline":"midnightblue"}
        if theme == "electric":
            colours = {"Done":"#87F5FB",
             "In Progress":"#DE3C4B",
             "Pending" : "#240115",
             "Current Date":"#4C956C",
             "Predicted End Date": "#788AA3",
             "Iteration 3 Demo": "indigo",
             "Trendline":"midnightblue"}
        if theme == "pastels":
            colours = {"Done":"#0FA3B1",
             "In Progress":"#B5E2FA",
             "Pending" : "#F7A072",
             "Current Date":"#9FB798",#554348" dark grey
             "Predicted End Date": "#EDB6A3",#3B7080",
             "Iteration 3 Demo": "#764248",#788AA3",#DDBDD5",
             "Trendline":"#5F634F"}       
        return(colours)
