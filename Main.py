import pandas as reader
import matplotlib.pyplot as plt
from Utils import format_e164, unix_to_stdtime, phone_book, regexp

reader.options.display.max_rows = 9999

call_type = []
call_status = []
aux = {'Quantity': [], 'Call ID': [], 'Month': [], 'Date & Time': [], 'Description': [], 'Calling number': [],
       'Original called number': [], 'Call status': [], 'Answered by': [], 'Answering time': []}
hunt_groups = ['IOC_HuntGroup', 'Sales_HuntGroup']
ioc_call_answer = []
sales_call_answer = []

if __name__ == '__main__':
    # List of relevant columns required in the report
    required_clns = ["globalCallID_callId", "dateTimeOrigination", "callingPartyNumber", "originalCalledPartyNumber",
                     "finalCalledPartyNumber", "dateTimeConnect", "dateTimeDisconnect", "destMobileDeviceName",
                     "duration"]

    # CDR file to be converted. ** Need to automate the file/location selection when running the code **
    #cdr = reader.read_csv('566C9E2E19443043E25F6D2D209FF9AB2022718123339452CDR.csv')
    cdr = reader.read_csv('IDS-Indata-July2022.csv')

    # Removing useless columns
    for item in cdr:
        if item not in required_clns:
            cdr = cdr.drop(item, axis=1)

    # Renaming the standard columns
    cdr.rename(columns={'globalCallID_callId': 'Call ID', 'dateTimeOrigination': 'Date & Time',
                        'callingPartyNumber': 'Calling number', 'originalCalledPartyNumber': 'Original called number',
                        'finalCalledPartyNumber': 'Final called number',
                        'dateTimeConnect': 'Date & Time call answer', 'dateTimeDisconnect': 'Disconnection time',
                        'lastRedirectDn': 'Last redirect extension', 'destMobileDeviceName': 'Sent to Microsoft Teams',
                        'duration': 'Duration'},
               inplace=True)

    # Converting unix timestamp to standard
    cdr['Date & Time'] = cdr['Date & Time'].apply(unix_to_stdtime)
    cdr['Date & Time call answer'] = cdr['Date & Time call answer'].apply(unix_to_stdtime)
    cdr['Disconnection time'] = cdr['Disconnection time'].apply(unix_to_stdtime)

    # Formatting E164 and unknown numbers
    cdr['Calling number'] = cdr['Calling number'].apply(format_e164)
    cdr['Original called number'] = cdr['Original called number'].apply(format_e164)
    cdr['Final called number'] = cdr['Final called number'].apply(format_e164)

    # Setting the call type
    for index, row in cdr.iterrows():
        src_internal = True
        dst_internal = True
        call_answered = True
        src_number = str(row['Calling number']).strip()
        dst_number = str(row['Original called number']).strip()

        if not regexp.search(src_number): src_internal = False
        if not regexp.search(dst_number): dst_internal = False
        if row['Duration'] == 0: call_answered = False

        if src_internal and dst_internal:
            call_type.append('Internal')
            if call_answered:
                call_status.append('Answered')
            else:
                call_status.append('Unanswered')
        elif src_internal and not dst_internal:
            call_type.append('Outgoing')
            if call_answered:
                call_status.append('Answered')
            else:
                call_status.append('Unanswered')
        elif not src_internal and dst_internal:
            call_type.append('Incoming')
            if call_answered:
                call_status.append('Answered')
            else:
                call_status.append('Unanswered')
        else:
            call_type.append('Unknown')
            call_status.append('N/A')
    cdr.insert(2, 'Call type', call_type)
    cdr.insert(3, 'Status', call_status)

    # Translating the extensions into user IDs using the external phone_book file
    cdr = cdr.replace({'Calling number': phone_book})
    cdr = cdr.replace({'Original called number': phone_book})
    cdr = cdr.replace({'Final called number': phone_book})

    # Sorting the entries to group details from same call ID and correct order for each call leg
    cdr = cdr.sort_values(by='Call ID', ascending=True)

    # Writer to Excel and writing the datasheet 'Calls'
    writer = reader.ExcelWriter("IDS_CDR_Test.xlsx", engine='xlsxwriter')
    cdr.to_excel(writer, sheet_name='Calls', header=False, startrow=1, index=False)
    worksheet = writer.sheets['Calls']
    worksheet.hide()
    workbook = writer.book
    worksheet.freeze_panes(1, 0)

    # Writing the columns names
    for column, value in enumerate(cdr.columns.values):
        worksheet.write(0, column, value)

    # Adding filters to each column
    row, column = cdr.shape
    worksheet.autofilter(0, 0, row, column - 1)

    # Creating 'Details' tab - Filtering to avoid different call legs being counted as different calls
    for idx, rows in cdr.iterrows():
        incoming = False
        # Append the details of current row if the call ID does not exist in the call list
        if rows['Call ID'] not in aux['Call ID']:
            aux['Call ID'].append(rows['Call ID'])
            aux['Month'].append(rows['Date & Time'])
            aux['Date & Time'].append(rows['Date & Time'])
            aux['Answering time'].append(rows['Date & Time call answer'])
            aux['Calling number'].append(rows['Calling number'])
            aux['Original called number'].append(rows['Original called number'])
            aux['Quantity'].append(1)

            if rows['Call type'] == 'Incoming':
                # Filtering incoming call legs to Unity, hunt-groups and users
                if rows['Final called number'] == 'Unity_VM_AA':
                    aux['Call status'].append('Unanswered / Abandoned')
                    aux['Answered by'].append('N/A')
                else:
                    aux['Call status'].append(rows['Status'])
                    if rows['Status'] == 'Answered':
                        if rows['Final called number'] not in hunt_groups:
                            aux['Answered by'].append(rows['Final called number'])
                        else:
                            aux['Answered by'].append(rows['Sent to Microsoft Teams'])
                    else:
                        aux['Answered by'].append('N/A')

                # Setting tags on calls to IOC or Sales
                if rows['Original called number'] == 'IOCMainLine#1240':
                    aux['Description'].append('To Operations Centre')
                    aux['Original called number'][-1] = 'IOCMainLine#1240'
                elif rows['Original called number'] == 'SalesMainLine#1230':
                    aux['Description'].append('To Sales Ops')
                    aux['Original called number'][-1] = 'SalesMainLine#1230'
                else:
                    aux['Description'].append(f'Incoming call to user')

            # Setting call types other than Incoming
            elif rows['Call type'] == 'Internal':
                aux['Description'].append('Internal call')
                aux['Call status'].append(rows['Status'])
                if rows['Status'] == 'Answered':
                    if rows['Final called number'] not in hunt_groups:
                        aux['Answered by'].append(rows['Final called number'])
                    else:
                        aux['Answered by'].append(rows['Sent to Microsoft Teams'])
                else:
                    aux['Answered by'].append('N/A')

            elif rows['Call type'] == 'Outgoing':
                aux['Description'].append('Outgoing call')
                aux['Call status'].append(rows['Status'])
                if rows['Status'] == 'Answered':
                    if rows['Final called number'] not in hunt_groups:
                        aux['Answered by'].append(rows['Final called number'])
                    else:
                        aux['Answered by'].append(rows['Sent to Microsoft Teams'])
                else:
                    aux['Answered by'].append('N/A')

            else:
                aux['Description'].append('General')
                aux['Call status'].append('N/A')
                aux['Answered by'].append('N/A')

        else:
            # Updating details of existing calls in the list to get the correct details for "status" and "answered by"
            if rows['Date & Time call answer'] > aux['Answering time'][-1]:
                aux['Call status'][-1] = 'Answered'
                if aux['Answered by'][-1] == 'N/A':
                    aux['Answering time'][-1] = rows['Date & Time call answer']
                    if rows['Final called number'] not in hunt_groups:
                        aux['Answered by'][-1] = rows['Final called number']
                    else:
                        aux['Answered by'][-1] = rows['Sent to Microsoft Teams']
            else:
                if rows['Original called number'] == 'IOCMainLine#1240':
                    aux['Description'][-1] = 'To Operations Centre'
                    aux['Original called number'][-1] = 'IOCMainLine#1240'
                if rows['Original called number'] == 'SalesMainLine#1230':
                    aux['Description'][-1] = 'To Sales Ops'
                    aux['Original called number'][-1] = 'SalesMainLine#1230'
                if rows['Final called number'] != 'Unity_VM_AA':
                    if rows['Final called number'] not in hunt_groups:
                        aux['Answered by'][-1] = rows['Final called number']
                    else:
                        aux['Answered by'][-1] = rows['Sent to Microsoft Teams']

    # Converting the dictionary into a dataframe (worksheet), converting 'Month' to show only its name
    call_filtered_list = reader.DataFrame(aux)
    call_filtered_list['Month'] = reader.to_datetime(call_filtered_list['Month']).dt.strftime("%b")
    call_filtered_list.to_excel(writer, sheet_name='Details', header=True, startrow=0, index=False)
    filtersheet = writer.sheets['Details']
    filtersheet.autofilter(0, 0, row, column - 1)
    filtersheet.freeze_panes(1, 0)
    filtersheet.activate()  # Required to hide 'Calls' tab - filtersheet is now the active (primary) sheet.

    # Creating a new dataframe from call_filtered_list and converting into a Pivot
    # This Pivot will summarize call by category, quantity and month
    pvt_calls_sum = call_filtered_list.groupby(['Month', 'Description'], as_index=False)['Quantity'].sum()
    pvt_calls_sum = (pvt_calls_sum.pivot(index='Month', columns='Description', values='Quantity').
                     rename_axis(None, axis=1).reset_index())
    pvt_calls_sum = pvt_calls_sum.fillna(0)
    pvt_calls_sum.to_excel(writer, sheet_name='Pvt-Sum-Categ', header=True, startrow=0, index=False)
    calls_sum_sheet = writer.sheets['Pvt-Sum-Categ']
    calls_sum_sheet.hide()

    # Creating a new dataframe from call_filtered_list and converting into a Pivot
    # This Pivot will summarize call by answering status, quantity and description
    pvt_calls_answer = call_filtered_list.groupby(['Description', 'Call status'], as_index=False)['Quantity'].sum()
    pvt_calls_answer = (pvt_calls_answer.pivot(index='Description', columns='Call status', values='Quantity').
                        rename_axis(None, axis=1).reset_index())
    pvt_calls_answer = pvt_calls_answer.fillna(0)
    pvt_calls_answer.to_excel(writer, sheet_name='Pvt-Sum-Stats', header=True, startrow=0, index=False)
    calls_answer_sheet = writer.sheets['Pvt-Sum-Stats']
    calls_answer_sheet.hide()

    # Setting a new dataframe for Summary tab
    summary = reader.DataFrame()
    summary.to_excel(writer, sheet_name='Summary', header=False, startrow=0, index=False)
    sumsheet = writer.sheets['Summary']
    sumsheet.insert_image('A1', r'Images/call_centre2.JPG')
    sumsheet.insert_image('A1', r'Images/IDS-Logo2.JPG')

    # Creating a bar plot using the information contained in calls_sum_sheet (Pvt-Sum-Categ)
    pvt_calls_sum.plot(x='Month', y=['Outgoing call', 'Incoming call to user', 'To Sales Ops', 'To Operations Centre'],
                       kind='bar', fontsize=8, rot=0)
    plt.title('Summary by category', fontsize='16')
    plt.xlabel('Month(s)', fontsize='11', labelpad=4)
    plt.ylabel('Total', fontsize='14')
    plt.grid(color='w', linestyle='solid')
    plt.savefig(r'Images/call_summ.JPEG')
    sumsheet.insert_image('A25', r'Images/call_summ.JPEG')

    pvt_calls_answer.plot(x='Description', y=['Answered', 'Unanswered', 'Unanswered / Abandoned', 'N/A'],
                          kind='bar', fontsize=5, rot=0)
    plt.title('Call handling summary', fontsize='16')
    plt.xlabel('Category', fontsize='11', labelpad=4)
    plt.ylabel('Total in this period', fontsize='14')
    plt.savefig(r'Images/call_handling.JPEG')
    sumsheet.insert_image('J25', r'Images/call_handling.JPEG')

    writer.save()
