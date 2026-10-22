"""Pocket Atlas: PyQt6 personal expense manager, six screens and a menu bar."""
import csv
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path
if '--self-test' in sys.argv:
    os.environ['QT_QPA_PLATFORM']='offscreen'
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QApplication,QMainWindow,QWidget,QFrame,QVBoxLayout,QHBoxLayout,QGridLayout,
    QStackedWidget,QScrollArea,QLineEdit,QTextEdit,QComboBox,QDoubleSpinBox,QDateEdit,QCheckBox,
    QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QMessageBox,QFileDialog)
from database import Database,TYPES,KINDS
from ui import STYLE,label,button,panel,stat,heading,BarChart


def rupees(paise):
    return f'₹{paise/100:,.2f}'


def clear(layout):
    while layout.count():
        item=layout.takeAt(0)
        if item.widget():
            item.widget().hide();item.widget().deleteLater()
        elif item.layout():
            clear(item.layout())


def combo(values):
    item=QComboBox();item.addItems(values);return item


def amount():
    item=QDoubleSpinBox();item.setRange(0,10000000);item.setDecimals(2);item.setPrefix('₹ ');return item


def date_edit(month=False):
    item=QDateEdit(QDate.currentDate());item.setCalendarPopup(True);item.setDisplayFormat('MMM yyyy' if month else 'dd MMM yyyy');return item


def field(layout,caption,control):
    layout.addWidget(label(caption.upper(),'micro'));layout.addWidget(control);return control


def table(headers):
    item=QTableWidget(0,len(headers));item.setHorizontalHeaderLabels(headers)
    item.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    item.verticalHeader().setVisible(False);item.verticalHeader().setDefaultSectionSize(45)
    item.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    item.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    item.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);item.setAlternatingRowColors(True);item.setMinimumHeight(220)
    return item


def fill(widget,rows,columns):
    widget.blockSignals(True);widget.setRowCount(len(rows))
    for index,row in enumerate(rows):
        for column,key in enumerate(columns):
            value=row.get(key,'')
            value=rupees(value) if key in ('amount','opening','balance','spent') else str(value)
            item=QTableWidgetItem(value);item.setData(Qt.ItemDataRole.UserRole,row['id']);widget.setItem(index,column,item)
    widget.clearSelection();widget.blockSignals(False)


class PocketAtlas(QMainWindow):
    PAGES=('Overview','Transactions','Accounts','Categories','Budgets','Reports')
    TABLES={1:'transactions',2:'accounts',3:'categories',4:'budgets'}

    def __init__(self,database=None):
        super().__init__()
        self.store=database or Database();self.loading=True;self.dirty=False;self.closing=False;self.current_page=0
        self.ids={t:None for t in self.TABLES.values()}
        self.setWindowTitle('Pocket Atlas — Personal Expense Manager · Practical 30')
        self.resize(1420,930);self.setMinimumSize(1120,780);self.setStyleSheet(STYLE)
        self.make_menu()
        root=QWidget();root.setObjectName('root');self.setCentralWidget(root)
        shell=QHBoxLayout(root);shell.setContentsMargins(0,0,0,0);shell.setSpacing(0)
        rail=QFrame();rail.setObjectName('rail');rail.setFixedWidth(194)
        rl=QVBoxLayout(rail);rl.setContentsMargins(18,28,18,24);rl.setSpacing(10)
        brand=label('◎');brand.setStyleSheet('font-size:44px;color:#cddd9d;');rl.addWidget(brand)
        rl.addWidget(label('Pocket\nAtlas','brand'));rl.addWidget(label('KNOW YOUR EVERYDAY.','railMicro'));rl.addSpacing(30)
        self.nav=[]
        for i,name in enumerate(self.PAGES):
            b=button(f'{i+1:02}   {name}',lambda checked=False,p=i:self.navigate(p),'nav');b.setCheckable(True);rl.addWidget(b);self.nav.append(b)
        rl.addStretch();rl.addWidget(label('A CLEARER PICTURE.\nA LITTLE MORE INTENTION.','railMicro'));rl.addSpacing(15)
        rl.addWidget(label('Your money. Your device.\nNo bank connection needed.','railText'));rl.addSpacing(15);rl.addWidget(label('30 / PERSONAL EXPENSES','railMicro'))
        shell.addWidget(rail)
        body=QWidget();bl=QVBoxLayout(body);bl.setContentsMargins(27,21,27,18);bl.setSpacing(15);shell.addWidget(body,1)
        top=QHBoxLayout();top.addWidget(label('YOUR PERSONAL MONEY MAP / INR','micro'));top.addStretch()
        top.addWidget(button('Import JSON',self.import_json));top.addWidget(button('Export JSON',self.export_json));top.addWidget(button('+ Transaction',self.new_transaction,'primary'));bl.addLayout(top)
        self.stack=QStackedWidget();bl.addWidget(self.stack,1)
        for build in (self.build_overview,self.build_transactions,self.build_accounts,self.build_categories,self.build_budgets,self.build_reports):
            self.stack.addWidget(build())
        self.notice=label('Start by adding an account and a category, then record your first transaction.','notice',True);bl.addWidget(self.notice)
        self.refresh();self.load_record('accounts',None);self.load_record('categories',None);self.load_record('transactions',None);self.load_record('budgets',None)
        self.loading=False;self.dirty=False;self.update_nav()

    def make_menu(self):
        file=self.menuBar().addMenu('&File')
        for caption,callback,shortcut in [('New transaction',self.new_transaction,'Ctrl+N'),('Import JSON',self.import_json,'Ctrl+I'),('Export JSON',self.export_json,'Ctrl+E'),('Export report CSV',self.export_csv,None),('Exit',self.close,'Ctrl+Q')]:
            action=QAction(caption,self)
            if shortcut:action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(callback);file.addAction(action)
        view=self.menuBar().addMenu('&Go to')
        for index,caption in enumerate(self.PAGES):
            action=QAction(caption,self);action.triggered.connect(lambda checked=False,p=index:self.navigate(p));view.addAction(action)
        help_menu=self.menuBar().addMenu('&Help')
        action=QAction('About Pocket Atlas',self);action.triggered.connect(lambda:QMessageBox.information(self,'Pocket Atlas','Personal Expense Manager\nPractical 30 · Python / PyQt6 / SQLite\nAll amounts are INR. Balances reflect your recorded transactions.'));help_menu.addAction(action)

    def page(self,eyebrow,title,description):
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content=QWidget();layout=QVBoxLayout(content);layout.setContentsMargins(0,0,9,0);layout.setSpacing(13)
        heading(layout,eyebrow,title,description);scroll.setWidget(content);return scroll,layout

    def watch(self,controls):
        for c in controls:
            if isinstance(c,(QLineEdit,QTextEdit)):c.textChanged.connect(self.mark_dirty)
            elif isinstance(c,QComboBox):c.currentIndexChanged.connect(self.mark_dirty)
            elif isinstance(c,QDateEdit):c.dateChanged.connect(self.mark_dirty)
            elif isinstance(c,QDoubleSpinBox):c.valueChanged.connect(self.mark_dirty)

    def build_overview(self):
        page,layout=self.page('01 / A map, not a mystery','Make sense of the small things.','The everyday choices add up. Give them a little context.')
        self.overview_stats=QHBoxLayout();layout.addLayout(self.overview_stats)
        self.account_cards=QHBoxLayout();layout.addLayout(self.account_cards)
        layout.addWidget(label('The latest on your ledger','section'))
        self.recent=table(('DATE','TRANSACTION','CATEGORY','TYPE','AMOUNT'));layout.addWidget(self.recent)
        self.demo=button('Explore with clearly labelled demo data',self.load_demo);layout.addWidget(self.demo)
        layout.addWidget(label('Recorded balance includes account opening balances and all saved transactions. Monthly totals use the current calendar month.','muted',True));layout.addStretch();return page

    def actions(self,layout,kind,caption):
        row=QHBoxLayout();row.addWidget(button(caption,lambda:self.save_record(kind),'primary'));row.addWidget(button('+ New',lambda:self.new_record(kind)));row.addStretch()
        delete=button('Delete selected',lambda:self.delete_record(kind),'danger');row.addWidget(delete);layout.addLayout(row)
        return delete

    def build_transactions(self):
        page,layout=self.page('02 / Every entry tells a story','Your everyday ledger.','Record income and expenses, refine the details, and keep your notes close.')
        filters=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Search title, category or notes…');self.kind_filter=combo(('All types',*KINDS))
        filters.addWidget(self.search,1);filters.addWidget(self.kind_filter);layout.addLayout(filters)
        self.transaction_table=table(('DATE','TRANSACTION','ACCOUNT','CATEGORY','TYPE','AMOUNT'));layout.addWidget(self.transaction_table)
        self.transaction_table.itemSelectionChanged.connect(lambda:self.choose('transactions',self.transaction_table))
        form=panel();fl=QHBoxLayout(form);left,right=QVBoxLayout(),QVBoxLayout();fl.addLayout(left,1);fl.addLayout(right,1)
        self.t_title=field(left,'Transaction title *',QLineEdit());self.t_account=field(left,'Account *',QComboBox());self.t_category=field(left,'Category *',QComboBox())
        self.t_amount=field(right,'Amount *',amount());self.t_date=field(right,'Date',date_edit());self.t_note=QTextEdit();self.t_note.setFixedHeight(82);field(right,'A note for later',self.t_note)
        layout.addWidget(form);self.t_delete=self.actions(layout,'transactions','Save transaction ↗');layout.addStretch()
        self.search.textChanged.connect(self.refresh_transactions);self.kind_filter.currentIndexChanged.connect(self.refresh_transactions)
        self.watch((self.t_title,self.t_account,self.t_category,self.t_amount,self.t_date,self.t_note));return page

    def build_accounts(self):
        page,layout=self.page('03 / Where your money lives','Give every rupee a home.','Create bank, cash, wallet or savings accounts. Opening balances are separate from income.')
        self.account_table=table(('ACCOUNT','TYPE','OPENING','RECORDED BALANCE'));layout.addWidget(self.account_table)
        self.account_table.itemSelectionChanged.connect(lambda:self.choose('accounts',self.account_table))
        form=panel();fl=QVBoxLayout(form)
        self.a_name=field(fl,'Account name *',QLineEdit());self.a_type=field(fl,'Account type',combo(TYPES));self.a_opening=field(fl,'Opening balance',amount())
        layout.addWidget(form);self.a_delete=self.actions(layout,'accounts','Save account ↗');layout.addStretch();self.watch((self.a_name,self.a_type,self.a_opening));return page

    def build_categories(self):
        page,layout=self.page('04 / A little organisation goes a long way','Find the patterns.','Categories connect your transactions, budgets and reports.')
        self.category_table=table(('CATEGORY','TYPE'));layout.addWidget(self.category_table)
        self.category_table.itemSelectionChanged.connect(lambda:self.choose('categories',self.category_table))
        form=panel();fl=QVBoxLayout(form);self.c_name=field(fl,'Category name *',QLineEdit());self.c_kind=field(fl,'Income or expense',combo(KINDS));layout.addWidget(form)
        layout.addWidget(label('A category already used by records cannot switch type; that would change the meaning of your ledger.','muted',True))
        self.c_delete=self.actions(layout,'categories','Save category ↗');layout.addStretch();self.watch((self.c_name,self.c_kind));return page

    def build_budgets(self):
        page,layout=self.page('05 / Make room for what matters','A little intention, month by month.','Set one monthly limit per expense category and compare it with your recorded spending.')
        self.budget_table=table(('MONTH','CATEGORY','LIMIT','SPENT'));layout.addWidget(self.budget_table)
        self.budget_table.itemSelectionChanged.connect(lambda:self.choose('budgets',self.budget_table))
        form=panel();fl=QVBoxLayout(form);self.b_category=field(fl,'Expense category *',QComboBox());self.b_month=field(fl,'Budget month',date_edit(True));self.b_amount=field(fl,'Monthly limit *',amount());layout.addWidget(form)
        self.b_delete=self.actions(layout,'budgets','Save budget ↗');layout.addStretch();self.watch((self.b_category,self.b_month,self.b_amount));return page

    def build_reports(self):
        page,layout=self.page('06 / A clearer picture','See where it all goes.','Filter the ledger by date, account and type. Export exactly the records shown below.')
        filters=QHBoxLayout();self.report_start=date_edit();self.report_start.setDate(QDate.currentDate().addDays(1-QDate.currentDate().day()));self.report_end=date_edit()
        self.report_kind=combo(('All types',*KINDS));self.report_account=QComboBox()
        for caption,control in [('FROM',self.report_start),('TO',self.report_end),('TYPE',self.report_kind),('ACCOUNT',self.report_account)]:
            block=QVBoxLayout();block.addWidget(label(caption,'micro'));block.addWidget(control);filters.addLayout(block,1)
        layout.addLayout(filters)
        row=QHBoxLayout();row.addWidget(button('Apply filters',self.refresh_reports,'primary'));row.addWidget(button('Export this report as CSV',self.export_csv));row.addStretch();layout.addLayout(row)
        self.report_stats=QHBoxLayout();layout.addLayout(self.report_stats)
        self.report_table=table(('DATE','TRANSACTION','ACCOUNT','CATEGORY','TYPE','AMOUNT'));layout.addWidget(self.report_table)
        self.chart_layout=QVBoxLayout();layout.addLayout(self.chart_layout);layout.addStretch();return page

    def mark_dirty(self,*_):
        if not self.loading and self.current_page in self.TABLES:self.dirty=True

    def message(self,value,error=False):
        self.notice.setText(value);self.notice.setProperty('error',error);self.notice.style().unpolish(self.notice);self.notice.style().polish(self.notice)

    def confirm_unsaved(self):
        if not self.dirty:return True
        result=QMessageBox.question(self,'Keep your changes?','Save this form before continuing?',QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Save)
        if result==QMessageBox.StandardButton.Cancel:return False
        return self.save_record(self.TABLES[self.current_page]) if result==QMessageBox.StandardButton.Save else True

    def navigate(self,index):
        if index==self.current_page:self.update_nav();return True
        if not self.confirm_unsaved():self.update_nav();return False
        self.current_page=index;self.stack.setCurrentIndex(index);self.refresh()
        if index in self.TABLES:self.load_record(self.TABLES[index],self.ids[self.TABLES[index]])
        self.dirty=False;self.update_nav();return True

    def update_nav(self):
        for i,b in enumerate(self.nav):b.setChecked(i==self.current_page)

    def populate(self,widget,rows,empty):
        selected=widget.currentData();widget.blockSignals(True);widget.clear();widget.addItem(empty,None)
        for row in rows:widget.addItem(row['name'],row['id'])
        widget.setCurrentIndex(max(0,widget.findData(selected)));widget.blockSignals(False)

    def refresh(self):
        if self.closing:return
        accounts,categories=self.store.accounts(),self.store.categories()
        for control,empty in [(self.t_account,'Choose account'),(self.report_account,'All accounts')]:self.populate(control,accounts,empty)
        self.populate(self.t_category,categories,'Choose category');self.populate(self.b_category,[c for c in categories if c['kind']=='Expense'],'Choose expense category')
        fill(self.account_table,accounts,('name','type','opening','balance'));fill(self.category_table,categories,('name','kind'));fill(self.budget_table,self.store.budgets(),('month','category','amount','spent'))
        self.refresh_transactions();self.refresh_reports()
        rows=self.store.transactions();fill(self.recent,rows[:7],('date','title','category','kind','amount'))
        month=date.today().isoformat()[:7];monthly=[t for t in rows if t['date'].startswith(month)]
        income=sum(t['amount'] for t in monthly if t['kind']=='Income');expense=sum(t['amount'] for t in monthly if t['kind']=='Expense')
        clear(self.overview_stats)
        for value,caption in [(rupees(sum(a['balance'] for a in accounts)),'Recorded balance'),(rupees(income),'Income this month'),(rupees(expense),'Expenses this month')]:self.overview_stats.addWidget(stat(value,caption))
        clear(self.account_cards)
        for account in accounts[:3]:self.account_cards.addWidget(stat(rupees(account['balance']),account['name']))
        self.demo.setVisible(not accounts and not categories and not rows)

    def refresh_transactions(self,*_):
        if hasattr(self,'transaction_table') and not self.closing:
            fill(self.transaction_table,self.store.transactions(self.search.text(),kind=self.kind_filter.currentText()),('date','title','account','category','kind','amount'))

    def refresh_reports(self):
        try:
            rows=self.store.transactions(start=self.report_start.date().toString('yyyy-MM-dd'),end=self.report_end.date().toString('yyyy-MM-dd'),kind=self.report_kind.currentText(),account=self.report_account.currentData())
            self.report_rows=rows;fill(self.report_table,rows,('date','title','account','category','kind','amount'))
            income=sum(t['amount'] for t in rows if t['kind']=='Income');expense=sum(t['amount'] for t in rows if t['kind']=='Expense');clear(self.report_stats)
            for value,caption in [(rupees(income),'Filtered income'),(rupees(expense),'Filtered expenses'),(rupees(income-expense),'Net movement')]:self.report_stats.addWidget(stat(value,caption))
            grouped={}
            for row in rows:
                if row['kind']=='Expense':grouped[row['category']]=grouped.get(row['category'],0)+row['amount']
            clear(self.chart_layout);self.chart_layout.addWidget(BarChart('Expense by category · ₹',[(name,round(value/100,2)) for name,value in grouped.items()] or [('No expenses in this view',0)]))
            return True
        except Exception as exc:
            if hasattr(self,'notice'):self.message(str(exc),True)
            return False

    def load_record(self,kind,key):
        self.loading=True;r=self.store.get(kind,key) if key else None;self.ids[kind]=r['id'] if r else None
        if kind=='accounts':
            self.a_name.setText(r['name'] if r else '');self.a_type.setCurrentText(r['type'] if r else 'Bank');self.a_opening.setValue(r['opening']/100 if r else 0);self.a_delete.setEnabled(bool(r))
        elif kind=='categories':
            self.c_name.setText(r['name'] if r else '');self.c_kind.setCurrentText(r['kind'] if r else 'Expense');self.c_delete.setEnabled(bool(r))
        elif kind=='transactions':
            self.t_title.setText(r['title'] if r else '');self.t_note.setPlainText(r['note'] if r else '');self.t_amount.setValue(r['amount']/100 if r else 0)
            self.t_date.setDate(QDate.fromString(r['date'],'yyyy-MM-dd') if r else QDate.currentDate())
            for widget,column in [(self.t_account,'account_id'),(self.t_category,'category_id')]:widget.setCurrentIndex(max(0,widget.findData(r[column] if r else None)))
            self.t_delete.setEnabled(bool(r))
        else:
            self.b_category.setCurrentIndex(max(0,self.b_category.findData(r['category_id'] if r else None)));self.b_month.setDate(QDate.fromString(r['month']+'-01','yyyy-MM-dd') if r else QDate.currentDate());self.b_amount.setValue(r['amount']/100 if r else 0);self.b_delete.setEnabled(bool(r))
        self.loading=False;self.dirty=False

    def save_record(self,kind):
        try:
            key=self.ids[kind]
            if kind=='accounts':key=self.store.save_account(self.a_name.text(),self.a_type.currentText(),self.a_opening.value(),key)
            elif kind=='categories':key=self.store.save_category(self.c_name.text(),self.c_kind.currentText(),key)
            elif kind=='transactions':key=self.store.save_transaction(self.t_title.text(),self.t_account.currentData(),self.t_category.currentData(),self.t_amount.value(),self.t_date.date().toString('yyyy-MM-dd'),self.t_note.toPlainText(),key)
            else:key=self.store.save_budget(self.b_category.currentData(),self.b_month.date().toString('yyyy-MM'),self.b_amount.value(),key)
            self.refresh();self.load_record(kind,key);self.message('Saved to your SQLite ledger.');return True
        except Exception as exc:self.message(str(exc),True);return False

    def choose(self,kind,widget):
        if widget.currentRow()<0:return
        item=widget.item(widget.currentRow(),0)
        if item and self.confirm_unsaved():self.load_record(kind,item.data(Qt.ItemDataRole.UserRole))

    def new_record(self,kind):
        if self.confirm_unsaved():self.load_record(kind,None)

    def new_transaction(self):
        if self.current_page==1:
            if not self.confirm_unsaved():return
        elif not self.navigate(1):return
        self.load_record('transactions',None);self.t_title.setFocus()

    def delete_record(self,kind):
        key=self.ids[kind]
        if key is None:return
        answer=QMessageBox.question(self,'Delete this record?','This permanently removes the selected record. Balances and reports will be recalculated.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
        if answer!=QMessageBox.StandardButton.Yes:return
        try:self.store.delete(kind,key);self.load_record(kind,None);self.refresh();self.message('Record deleted. Your ledger has been recalculated.')
        except Exception as exc:self.message(str(exc),True)

    def export_json(self):
        path,_=QFileDialog.getSaveFileName(self,'Export all saved records','pocket-atlas-export.json','JSON files (*.json)')
        if path:
            try:
                target=Path(path);temporary=target.with_name(target.name+'.tmp');temporary.write_text(json.dumps(self.store.export(),ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(target);self.message('JSON exported. This file can be imported back into Pocket Atlas.')
            except Exception as exc:self.message(str(exc),True)

    def import_json(self):
        path,_=QFileDialog.getOpenFileName(self,'Read a Pocket Atlas export','','JSON files (*.json)')
        if not path:return
        try:
            if Path(path).stat().st_size>25*1024*1024:raise ValueError('Choose an export smaller than 25 MB.')
            payload=json.loads(Path(path).read_text(encoding='utf-8-sig'));count=self.store.import_data(payload);self.refresh();self.message(f'{count} new records imported. Existing identifiers were skipped; your saved edits were kept.')
        except Exception as exc:self.message('Import failed: '+str(exc),True)

    def export_csv(self):
        if not self.refresh_reports():return
        path,_=QFileDialog.getSaveFileName(self,'Export filtered report','pocket-atlas-report.csv','CSV files (*.csv)')
        if path:
            try:
                with open(path,'w',encoding='utf-8-sig',newline='') as file:
                    writer=csv.writer(file);writer.writerow(('Date','Title','Account','Category','Type','Amount INR','Note'))
                    for t in self.report_rows:
                        values=[t['date'],t['title'],t['account'],t['category'],t['kind'],f"{t['amount']/100:.2f}",t['note']]
                        writer.writerow(["'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v for v in values])
                self.message('Filtered report exported as CSV. Use JSON export for data you want to read back into the app.')
            except Exception as exc:self.message(str(exc),True)

    def load_demo(self):
        if self.store.accounts() or self.store.categories():return
        try:
            account=self.store.save_account('Demo wallet','Cash',1500);food=self.store.save_category('Demo · Food','Expense');travel=self.store.save_category('Demo · Travel','Expense');income=self.store.save_category('Demo · Income','Income')
            today=date.today().isoformat();self.store.save_transaction('Demo · Lunch',account,food,120,today,'Sample record — replace with your own.');self.store.save_transaction('Demo · Bus ticket',account,travel,30,today,'Sample record');self.store.save_transaction('Demo · Pocket money',account,income,500,today,'Sample record');self.store.save_budget(food,today[:7],2000)
            self.refresh();self.message('Clearly labelled demo records loaded. Edit or delete them freely.')
        except Exception as exc:self.message(str(exc),True)

    def closeEvent(self,event):
        if self.confirm_unsaved():self.closing=True;self.store.close();event.accept()
        else:event.ignore()


if __name__=='__main__':
    application=QApplication(sys.argv);application.setStyle('Fusion');application.setApplicationName('Pocket Atlas')
    if '--self-test' in sys.argv:
        output=Path(sys.argv[sys.argv.index('--self-test')+1])
        try:
            with tempfile.TemporaryDirectory() as folder:
                database=Database(Path(folder)/'test.db');window=PocketAtlas(database);window.show();window.load_demo();application.processEvents()
                assert len(database.transactions())==3
                for index in range(6):
                    assert window.navigate(index)
                    application.processEvents()
                payload=database.export();other=Database(Path(folder)/'roundtrip.db');assert other.import_data(payload)==len(payload['accounts'])+len(payload['categories'])+len(payload['transactions'])+len(payload['budgets']);other.close()
                window.dirty=False;window.close();application.processEvents()
            output.write_text(json.dumps(dict(result='PASS',screens=6,checks=['packaged Qt startup','SQLite CRUD demo','six screens','JSON export/import']),indent=2))
            sys.exit(0)
        except Exception as error:
            output.write_text(json.dumps(dict(result='FAIL',error=str(error)),indent=2));sys.exit(1)
    else:
        window=PocketAtlas();window.show();sys.exit(application.exec())
