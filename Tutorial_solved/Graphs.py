def Dispatch_reg(model,sp_tech,sp_reg,weekly,pie_values='share',Unit='GWh',rnd=1,font=15):
    
    
    mnth=['Jan',
 'Jan0',
 'Jan1',
 'Jan2',
 'Jan3',
 'Feb',
 'Feb0',
 'Feb1',
 'Feb2',
 'Mar',
 'Mar0',
 'Mar1',
 'Mar2',
 'Apr',
 'Apr0',
 'Apr1',
 'Apr2',
 'May',
 'May0',
 'May1',
 'May2',
 'May3',
 'Jun',
 'Jun0',
 'Jun1',
 'Jun2',
 'Jul',
 'Jul0',
 'Jul1',
 'Jul2',
 'Aug',
 'Aug0',
 'Aug1',
 'Aug2',
 'Aug3',
 'Sept',
 'Sept0',
 'Sept1',
 'Sept2',
 'Oct',
 'Oct0',
 'Oct1',
 'Oct2',
 'Nov',
 'Nov0',
 'Nov1',
 'Nov2',
 'Dec',
 'Dec0',
 'Dec1',
 'Dec2','Dec3']
    
    
    
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib import gridspec
    
    # Reading Information from EXCEL File
    
    file = r'Graph_inputs.xlsx'
    Nodes = pd.read_excel(file,'Nodes',index_col=[0],header=[0])
    Dem_tech = pd.read_excel(file,'Demand Technology',index_col=[0],header=[0])
    Pps_tech = pd.read_excel(file,'PPs',index_col=[0],header=[0])
    Trans = pd.read_excel(file,'Transmission',index_col=[0],header=[0])
    Date = pd.read_excel(file,'Date',index_col=[0],header=[0])
    Colors = pd.read_excel(file,'Colors',index_col=[0],header=[0])
    
    day = Date.loc['day'].values[0]
    end = Date.loc['end'].values[0]
    
    # Conversion Factor
    cf = 1000000
    
    #Getting the time Indeces needed to build the dataframes
    ind = model.get_formatted_array('carrier_con').loc[{'techs':Dem_tech.values[0,0],'carriers':Dem_tech.values[0,1],'locs':[Nodes.values[0,0]]}].sum('locs').to_pandas().T
    ind = ind.index
    
    # Building the Demand Data Frame
    Demand_c = pd.DataFrame(0,index=ind , columns = Nodes['Location'].tolist())
    
    # Filling Demand DataFrame With Calliope Results 
    for i in range(len(Nodes)):    
        Demand_c[Nodes.values[i,0]] = -model.get_formatted_array('carrier_con').loc[{'techs':Dem_tech.values[0,0],'carriers':Dem_tech.values[0,1],'locs':[Nodes.values[i,0]]}].sum('locs').to_pandas().T
    
    # kW to GW
    Demand_c = Demand_c / cf
    Demand_c_cop = Demand_c.copy()
    tot_loc = Nodes['Location'].tolist()
    for i in range(len(tot_loc)):
        region = tot_loc[i]
        Demand = Demand_c_cop
        
        #Building The Production Data Frame
        Prod = pd.DataFrame(0,index = ind , columns=Pps_tech['Tech'].tolist())
        
    
        # Filling Production DataFrame With Calliope Results 
        for i in range (len(Pps_tech)):
            Prod[Pps_tech.values[i,0]] = model.get_formatted_array('carrier_prod').loc[{'techs':Pps_tech.values[i,0],'carriers':Dem_tech.values[0,1],'locs':[region]}].sum('locs').to_pandas().T
        prod_pie = Prod.copy()/cf
       
        # Make a copy of nodes because we will remove 1 node in every graph
        New_Nodes = Nodes.copy()
        New_Nodes = New_Nodes['Location'].tolist()
        New_Nodes.remove(region)
        exp_list = New_Nodes.copy()
        imp_list = New_Nodes.copy()
    
        # Building EXP / IMP Lists
        for i in range (len(New_Nodes)):
            exp_list[i] = exp_list[i] + '_exp'
            imp_list[i] = imp_list[i] + '_imp'
    
        #   Building EXP / IMP DataFrame  
        Exp_to = pd.DataFrame(0,index = ind , columns = exp_list)
        Imp_from = pd.DataFrame(0,index = ind , columns = imp_list)
    
        # Transmission Technologies List
        trans_list= Trans['Tech'].tolist()
    
        # Building The List of Transmission - Locations
        for i in range (len(trans_list)):
            trans_list[i] = trans_list[i] + ':'
    
        trans_loc = pd.DataFrame(0,index =trans_list,columns = New_Nodes )
    
        for i in range (len(trans_list)):
            for j in range (len(New_Nodes)):
                trans_loc.loc[trans_list[i],New_Nodes[j]] = trans_list[i] + New_Nodes[j]
    
        print('1')
        # Filling The Data of Exp and Imp with Calliope Results    
        for i in range (len(New_Nodes)):
            for j in range (len(trans_list)):
                Exp_to[exp_list[i]] = Exp_to[exp_list[i]].values + model.get_formatted_array('carrier_con').loc[{'techs':[trans_loc[New_Nodes[i]].tolist()[j]],'carriers':Dem_tech.values[0,1],'locs':[region]}].sum('locs').sum('techs').to_pandas().T
    
        for i in range(len(New_Nodes)):
            for j in range (len(trans_list)):
                Imp_from[imp_list[i]] = Imp_from[imp_list[i]].values + model.get_formatted_array('carrier_prod').loc[{'techs':[trans_loc[New_Nodes[i]].tolist()[j]],'carriers':Dem_tech.values[0,1],'locs':[region]}].sum('locs').sum('techs').to_pandas().T
    
        # Building The Production and Import DataFrame
        production = pd.DataFrame(0,index = ind , columns =Pps_tech['Tech'].tolist() + imp_list )
    
        full_prod_list = list(production.columns)
        for i in range (len(full_prod_list)):
            try:
                production[full_prod_list[i]] = Prod[full_prod_list[i]].values / cf
            except:
                production[full_prod_list[i]] = Imp_from[full_prod_list[i]].values / cf     
    
        Exp_to = Exp_to / cf
    

    
        # Making Cummulative Production And Consumption
        prod_cum = production.copy()
        for i in range (len(full_prod_list)-1):
            prod_cum[full_prod_list[i+1]] = prod_cum[full_prod_list[i]].values + prod_cum[full_prod_list[i+1]].values
    
        exp_cum = Exp_to.copy()  
        for i in range (len(exp_list)-1):
            exp_cum[exp_list[i+1]] = exp_cum[exp_list[i]].values + exp_cum[exp_list[i+1]].values
 
        
        week_list = []
        for j in range (52):
            for i in range(7):
                for h in range(24):
                    week_list.append('week_' + str(j+1))
        
        for i in range(24):   
            week_list.append('week_' + str(j+1))
            
        
        if weekly:
            prod_cum.index = week_list
            exp_cum.index = week_list
            Demand.index = week_list
            production.index = week_list
            
            
            prod_cum = prod_cum.groupby(week_list,sort=False).mean()      
            exp_cum = exp_cum.groupby(week_list,sort=False).mean()    
            Demand = Demand.groupby(week_list,sort=False).mean() 
            production = production.groupby(week_list,sort=False).mean() 

            prod_cum.index = mnth      
            exp_cum.index = mnth   
            Demand.index = mnth 
            production.index = mnth
            day = mnth[0]
            end = mnth[51]
            
        

        if sp_tech == False or sp_reg != region :
            

            
            # PLOT #
            fig, (ax1) = plt.subplots(1, figsize=(8,6))
            ax1.margins(x=0)
            ax1.margins(y=0.1)
            # Demand Plot
            ax1.plot(Demand[region][day:end].index,Demand[region][day:end].values,'#000000', alpha=0.5, linestyle = '-', label ='Demand')
        
            # Production Plot - Lines
            for i in range (len(full_prod_list)):
                ax1.plot(prod_cum[full_prod_list[i]][day:end].index,prod_cum[full_prod_list[i]][day:end].values,Colors.loc[full_prod_list[i],'Color'],alpha = 0.2)
        
            # Export Plots - Lines
            for i in range (len(exp_list)):
                ax1.plot(exp_cum[exp_list[i]][day:end].index,exp_cum[exp_list[i]][day:end].values,Colors.loc[exp_list[i],'Color'],alpha = 0.2)
        
            # Fill In Graphs - Production
            ax1.fill_between(prod_cum[full_prod_list[0]][day:end].index,0,prod_cum[full_prod_list[0]][day:end].values,facecolor = Colors.loc[full_prod_list[0],'Color'],alpha = 0.6,label =Colors.loc[full_prod_list[0],'Name'] )
        
            for i in range (len(full_prod_list)-1):
                ax1.fill_between(prod_cum[full_prod_list[0]][day:end].index,prod_cum[full_prod_list[i+1]][day:end].values,prod_cum[full_prod_list[i]][day:end].values,facecolor = Colors.loc[full_prod_list[i+1],'Color'],alpha = 0.6,label =Colors.loc[full_prod_list[i+1],'Name'] )
        
            # Fill In Graphs - Export
            ax1.fill_between(exp_cum[exp_list[0]][day:end].index,0,exp_cum[exp_list[0]][day:end].values,facecolor = Colors.loc[exp_list[0],'Color'],alpha = 0.6,label =Colors.loc[exp_list[0],'Name'] )
        
            for i in range (len(exp_list)-1):
                ax1.fill_between(exp_cum[exp_list[0]][day:end].index,exp_cum[exp_list[i+1]][day:end].values,exp_cum[exp_list[i]][day:end].values,facecolor = Colors.loc[exp_list[i+1],'Color'],alpha=0.6,label =Colors.loc[exp_list[i+1],'Name'])
    
        
            lgd2 = ax1.legend(loc=1,  bbox_to_anchor=(1.37, 1))
            ylbl = 'Power (GW)'
            ax1.set_ylabel(ylbl,labelpad = 11)
            if weekly:
                
                ax1.set_xticks([mnth[0],mnth[5],mnth[9],mnth[13],mnth[17],mnth[22],mnth[26],mnth[30],mnth[35],mnth[39],mnth[43],mnth[47]])#
                plt.xticks(rotation=70)
            ax1.set_title(region +' Region Energy Dispatch')
            fig.savefig(r'Graphs\ ' + region + '_Result.svg', dpi=fig.dpi,bbox_inches='tight')
            
            
        else:
            
            fig, (axs) = plt.subplots(2, figsize=(8,10),sharex=True)
            gs = gridspec.GridSpec(2, 1,height_ratios=[3,1]) 
            axs[1] = plt.subplot(gs[1])
            axs[0] = plt.subplot(gs[0],sharex=axs[1])
            
            axs[0].margins(x=0)
            axs[0].margins(y=0.0)
            
            plt.setp(axs[0].get_xticklabels(), visible=False)
            
            
            axs[0].plot(Demand[region][day:end].index,Demand[region][day:end].values,'#000000', alpha=0.5, linestyle = '-', label ='Demand')
            
            # Production Plot - Lines
            for i in range (len(full_prod_list)):
                axs[0].plot(prod_cum[full_prod_list[i]][day:end].index,prod_cum[full_prod_list[i]][day:end].values,Colors.loc[full_prod_list[i],'Color'],alpha = 0.2)
            
            # Export Plots - Lines
            for i in range (len(exp_list)):
                axs[0].plot(exp_cum[exp_list[i]][day:end].index,exp_cum[exp_list[i]][day:end].values,Colors.loc[exp_list[i],'Color'],alpha = 0.2)
            
            # Fill In Graphs - Production
            axs[0].fill_between(prod_cum[full_prod_list[0]][day:end].index,0,prod_cum[full_prod_list[0]][day:end].values,facecolor = Colors.loc[full_prod_list[0],'Color'],alpha = 0.6,label =Colors.loc[full_prod_list[0],'Name'] )
            
            for i in range (len(full_prod_list)-1):
                axs[0].fill_between(prod_cum[full_prod_list[0]][day:end].index,prod_cum[full_prod_list[i+1]][day:end].values,prod_cum[full_prod_list[i]][day:end].values,facecolor = Colors.loc[full_prod_list[i+1],'Color'],alpha = 0.6,label =Colors.loc[full_prod_list[i+1],'Name'] )
            
            # Fill In Graphs - Export
            axs[0].fill_between(exp_cum[exp_list[0]][day:end].index,0,exp_cum[exp_list[0]][day:end].values,facecolor = Colors.loc[exp_list[0],'Color'],alpha = 0.6,label =Colors.loc[exp_list[0],'Name'] )
            
            for i in range (len(exp_list)-1):
                axs[0].fill_between(exp_cum[exp_list[0]][day:end].index,exp_cum[exp_list[i+1]][day:end].values,exp_cum[exp_list[i]][day:end].values,facecolor = Colors.loc[exp_list[i+1],'Color'],alpha=0.6,label =Colors.loc[exp_list[i+1],'Name'])            
             
            lgd2 = axs[0].legend(loc=1,  bbox_to_anchor=(1.37, 1))
            ylbl = 'Power (GW)'
            axs[0].set_ylabel(ylbl,labelpad = 11)
            axs[0].set_title(region +' Region Energy Dispatch')
            

            axs[1].margins(x=0)
            axs[1].margins(y=0)
            axs[1].plot(production[sp_tech][day:end].index,production[sp_tech][day:end].values,'#000000', alpha=0.5)
            axs[1].fill_between(production[sp_tech][day:end].index,0,production[sp_tech][day:end].values,facecolor = Colors.loc[sp_tech,'Color'],alpha = 0.6,label =Colors.loc[sp_tech,'Name'])
            
            maxy = production[sp_tech].max()
            axs[1].set_ylim(0,maxy*1.1)
            
            lgd2 = axs[1].legend(loc=1,  bbox_to_anchor=(1.37, 1))
            ylbl = 'Power (GW)'
            axs[1].set_ylabel(ylbl,labelpad = 11)   
            chart = axs[1]
            if weekly:    
                axs[1].set_xticks([mnth[0],mnth[5],mnth[9],mnth[13],mnth[17],mnth[22],mnth[26],mnth[30],mnth[35],mnth[39],mnth[43],mnth[47]])
              
            fig.savefig(r'Graphs\ ' + region + '_Result.svg', dpi=fig.dpi,bbox_inches='tight')  

        
        # Pie Chart
        if pie_values=='share':
            my_pie = pd.DataFrame(((prod_pie.sum().values/prod_pie.sum().sum())*100).round(rnd),index=prod_pie.columns.to_list(),columns=['Share'])

        elif pie_values == 'value':
            if Unit== 'GWh':
                my_pie = pd.DataFrame((prod_pie.sum().values).round(rnd),index=prod_pie.columns.to_list(),columns=['GWh'])
            elif Unit =='TWh':
                my_pie = pd.DataFrame((prod_pie.sum().values/1000.0).round(rnd),index=prod_pie.columns.to_list(),columns=['TWh'])                
            
          
            

        elif pie_values != 'share' or pie_values != 'value':
            raise ValueError('the pie_values should be **share** or **value** ')
            
        myind = my_pie.index.to_list()
        pie_pps = []
        pie_cols = []
        
        for i in range(len(myind)):
            pie_pps.append(Colors.loc[myind[i],'Name'])
            pie_cols.append(Colors.loc[myind[i],'Color'])

        plt.figure(figsize=(10,10))
        plt.title('{} Production Mix'.format(region),fontname="Times New Roman",fontweight="bold",fontsize=24)
        plt.pie(my_pie.values,
                shadow=False, startangle=90,colors=pie_cols)
        
        
        #Add a table at the bottom of the axes
        the_table = plt.table(cellText=my_pie.values,
                              rowColours=pie_cols,
                              rowLabels= pie_pps,
                              colLabels = my_pie.columns,
                              loc='right',
                              rowLoc ='center',
                              colLoc='center',
                              cellLoc='center',bbox=(1.25,0.2,0.1,0.5)) 
        the_table.auto_set_font_size(False)
        the_table.set_fontsize(font)
        
        fig.savefig(r'Graphs\ ' + region + 'pie_Result.svg', dpi=fig.dpi,bbox_inches='tight')  
        

        
def Dispatch_sys(model,sp_tech,weekly=False,pie_values='share',Unit='GWh',rnd=1,font=15):
    mnth=['Jan',
 'Jan0',
 'Jan1',
 'Jan2',
 'Jan3',
 'Feb',
 'Feb0',
 'Feb1',
 'Feb2',
 'Mar',
 'Mar0',
 'Mar1',
 'Mar2',
 'Apr',
 'Apr0',
 'Apr1',
 'Apr2',
 'May',
 'May0',
 'May1',
 'May2',
 'May3',
 'Jun',
 'Jun0',
 'Jun1',
 'Jun2',
 'Jul',
 'Jul0',
 'Jul1',
 'Jul2',
 'Aug',
 'Aug0',
 'Aug1',
 'Aug2',
 'Aug3',
 'Sept',
 'Sept0',
 'Sept1',
 'Sept2',
 'Oct',
 'Oct0',
 'Oct1',
 'Oct2',
 'Nov',
 'Nov0',
 'Nov1',
 'Nov2',
 'Dec',
 'Dec0',
 'Dec1',
 'Dec2','Dec3']    
    
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib import gridspec
    
    # Reading Information from EXCEL File
    
    file = r'Graph_inputs.xlsx'
    Nodes = pd.read_excel(file,'Nodes',index_col=[0],header=[0])
    Dem_tech = pd.read_excel(file,'Demand Technology',index_col=[0],header=[0])
    Pps_tech = pd.read_excel(file,'PPs',index_col=[0],header=[0])   
    Date = pd.read_excel(file,'Date',index_col=[0],header=[0])
    Colors = pd.read_excel(file,'Colors',index_col=[0],header=[0])
    
    day = Date.loc['day'].values[0]
    end = Date.loc['end'].values[0]
    
    # Conversion Factor
    cf = 1000000
    
    #Getting the time Indeces needed to build the dataframes
    ind = model.get_formatted_array('carrier_con').loc[{'techs':Dem_tech.values[0,0],'carriers':Dem_tech.values[0,1],'locs':[Nodes.values[0,0]]}].sum('locs').to_pandas().T
    ind = ind.index
    
    # Building the Demand Data Frame
    Demand = pd.DataFrame(0,index=ind , columns = Nodes['Location'].tolist())
    
    # Filling Demand DataFrame With Calliope Results 
    for i in range(len(Nodes)):    
        Demand[Nodes.values[i,0]] = -model.get_formatted_array('carrier_con').loc[{'techs':Dem_tech.values[0,0],'carriers':Dem_tech.values[0,1],'locs':[Nodes.values[i,0]]}].sum('locs').to_pandas().T
    
    # kW to GW
    Demand = Demand / cf
    

    # Summing all the demands 
    Demand = pd.DataFrame(Demand.sum(axis=1),columns=['Value'])
    
    # Making the Lists
    Pps_list = Pps_tech['Tech'].tolist()
    Nodes_list = Nodes['Location'].tolist()

    # Building the Production DataFrame
    production = pd.DataFrame(0,index = ind, columns = Pps_list)
    
    # Reading the production results from Calliope
    for i in range (len(Pps_list)):
        for j in range(len(Nodes_list)):
            production[Pps_list[i]] = production[Pps_list[i]].values + model.get_formatted_array('carrier_prod').loc[{'techs':Pps_list[i],'carriers':Dem_tech.values[0,1],'locs':[Nodes_list[j]]}].sum('locs').to_pandas().T
    production = production / cf
    
    # Building the Cummulative Production
    prod_cum = production.copy()
    prod_pie = production.copy()
    for i in range (len(Pps_list)-1):
        prod_cum[Pps_list[i+1]] = prod_cum[Pps_list[i]].values + prod_cum[Pps_list[i+1]].values
    
    week_list = []
    for j in range (52):
        for i in range(7):
            for h in range(24):
                week_list.append('week_' + str(j+1))
        
    for i in range(24):   
        week_list.append('week_' + str(j+1))
            
        
    if weekly:
        prod_cum.index = week_list
        Demand.index = week_list
        production.index = week_list
            
            
        prod_cum = prod_cum.groupby(week_list,sort=False).mean()        
        Demand = Demand.groupby(week_list,sort=False).mean() 
        production = production.groupby(week_list,sort=False).mean() 
            

        prod_cum.index = mnth      
        Demand.index = mnth 
        production.index = mnth
        day = mnth[0]
        end = mnth[51]        
    if sp_tech == False:
        
        # PLOT
        fig, (ax1) = plt.subplots(1, figsize=(8,6))
        ax1.margins(x=0)
        ax1.margins(y=0.0)
        
        # Demand Plot
        ax1.plot(Demand['Value'][day:end].index,Demand['Value'][day:end].values,'#000000', alpha=0.5, linestyle = '-', label ='Demand')
        
        # Production Plot - Lines
        for i in range (len(Pps_list)):
            ax1.plot(prod_cum[Pps_list[i]][day:end].index,prod_cum[Pps_list[i]][day:end].values,Colors.loc[Pps_list[i],'Color'],alpha = 0.2)
        
        # Fill In Graphs - Production
        ax1.fill_between(prod_cum[Pps_list[0]][day:end].index,0,prod_cum[Pps_list[0]][day:end].values,facecolor = Colors.loc[Pps_list[0],'Color'],alpha = 0.6,label =Colors.loc[Pps_list[0],'Name'] )
        
        for i in range (len(Pps_list)-1):
            ax1.fill_between(prod_cum[Pps_list[0]][day:end].index,prod_cum[Pps_list[i+1]][day:end].values,prod_cum[Pps_list[i]][day:end].values,facecolor = Colors.loc[Pps_list[i+1],'Color'],alpha = 0.6,label =Colors.loc[Pps_list[i+1],'Name'] )
        
        lgd2 = ax1.legend(loc=1,  bbox_to_anchor=(1.45, 1))
        ylbl = 'Power (GW)'
        ax1.set_ylabel(ylbl,labelpad = 11)
        ax1.set_title('System Energy Dispatch')
        
        if weekly:
            
            plt.xticks(rotation=70)
            ax1.set_xticks([mnth[0],mnth[5],mnth[9],mnth[13],mnth[17],mnth[22],mnth[26],mnth[30],mnth[35],mnth[39],mnth[43],mnth[47]])      
        fig.savefig(r'Graphs\ ' +  'System_Result.svg', dpi=fig.dpi,bbox_inches='tight')
        
    else:
        # PLOT
        fig, (axs) = plt.subplots(2, figsize=(8,10),sharex=True)
        gs = gridspec.GridSpec(2, 1,height_ratios=[3,1]) 
        axs[1] = plt.subplot(gs[1])
        axs[0] = plt.subplot(gs[0],sharex=axs[1])
        
        axs[0].margins(x=0)
        axs[0].margins(y=0.0)
        
        plt.setp(axs[0].get_xticklabels(), visible=False)
        
        # Demand Plot
        axs[0].plot(Demand['Value'][day:end].index,Demand['Value'][day:end].values,'#000000', alpha=0.5, linestyle = '-', label ='Demand')
        
        # Production Plot - Lines
        for i in range (len(Pps_list)):
            axs[0].plot(prod_cum[Pps_list[i]][day:end].index,prod_cum[Pps_list[i]][day:end].values,Colors.loc[Pps_list[i],'Color'],alpha = 0.2)
        
        # Fill In Graphs - Production
        axs[0].fill_between(prod_cum[Pps_list[0]][day:end].index,0,prod_cum[Pps_list[0]][day:end].values,facecolor = Colors.loc[Pps_list[0],'Color'],alpha = 0.6,label =Colors.loc[Pps_list[0],'Name'] )
        
        for i in range (len(Pps_list)-1):
            axs[0].fill_between(prod_cum[Pps_list[0]][day:end].index,prod_cum[Pps_list[i+1]][day:end].values,prod_cum[Pps_list[i]][day:end].values,facecolor = Colors.loc[Pps_list[i+1],'Color'],alpha = 0.6,label =Colors.loc[Pps_list[i+1],'Name'] )
        
            
            
        lgd2 = axs[0].legend(loc=1,  bbox_to_anchor=(1.45, 1))
        ylbl = 'Power (GW)'
        axs[0].set_ylabel(ylbl,labelpad = 11)
        axs[0].set_title('System Energy Dispatch')
        
     
        
        axs[1].margins(x=0)
        axs[1].margins(y=0)
        axs[1].plot(production[sp_tech][day:end].index,production[sp_tech][day:end].values,'#000000', alpha=0.5)
        axs[1].fill_between(production[sp_tech][day:end].index,0,production[sp_tech][day:end].values,facecolor = Colors.loc[sp_tech,'Color'],alpha = 0.6,label =Colors.loc[sp_tech,'Name'])
        
        maxy = production[sp_tech].max()
        axs[1].set_ylim(0,maxy*1.1)
        
        lgd2 = axs[1].legend(loc=1,  bbox_to_anchor=(1.45, 1))
        ylbl = 'Power (GW)'
        axs[1].set_ylabel(ylbl,labelpad = 11)  
        
        if weekly:
            
            #ax.set_xticklabels(xlabels, rotation=45, rotation_mode="anchor") 
            #plt.xticks(rotation=70)
            axs[1].set_xticks([mnth[0],mnth[5],mnth[9],mnth[13],mnth[17],mnth[22],mnth[26],mnth[30],mnth[35],mnth[39],mnth[43],mnth[47]])          
        fig.savefig(r'Graphs\ ' +  sp_tech + ' Vs System_Result.svg', dpi=fig.dpi,bbox_inches='tight')
        
    if pie_values=='share':
        my_pie = pd.DataFrame(((prod_pie.sum().values/prod_pie.sum().sum())*100).round(rnd),index=prod_pie.columns.to_list(),columns=['Share'])
    
    elif pie_values == 'value':
            if Unit== 'GWh':
                my_pie = pd.DataFrame((prod_pie.sum().values).round(rnd),index=prod_pie.columns.to_list(),columns=['GWh'])
            elif Unit =='TWh':
                my_pie = pd.DataFrame((prod_pie.sum().values/1000.0).round(rnd),index=prod_pie.columns.to_list(),columns=['TWh'])         
        
    
    elif pie_values != 'share' or pie_values != 'value':
        raise ValueError('the pie_values should be **share** or **value** ')
        
    ind = my_pie.index.to_list()
    pie_pps = []
    pie_cols = []
    
    for i in range(len(ind)):
        pie_pps.append(Colors.loc[ind[i],'Name'])
        pie_cols.append(Colors.loc[ind[i],'Color'])
    
    plt.figure(figsize=(10,10))
    plt.title('System Energy Mix',fontname="Times New Roman",fontweight="bold",fontsize=24)
    plt.pie(my_pie.values,
            shadow=False, startangle=90,colors=pie_cols)
    
    
    #Add a table at the bottom of the axes
    the_table = plt.table(cellText=my_pie.values,
                          rowColours=pie_cols,
                          rowLabels= pie_pps,
                          colLabels = my_pie.columns,
                          loc='right',
                         rowLoc ='center',
                         colLoc='center',
                         cellLoc='center',bbox=(1.25,0.2,0.1,0.5)) 

    the_table.auto_set_font_size(False)
    the_table.set_fontsize(font)
    

    plt.subplots_adjust(bottom=0.1, right=0.8, top=0.9)         
    plt.savefig(r'Graphs\Pie_System_Result.svg', dpi=fig.dpi,bbox_inches='tight')
    plt.show()

        


        
        
        


        
        
        
        
        
        

       