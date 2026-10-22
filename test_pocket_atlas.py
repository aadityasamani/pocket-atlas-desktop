import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from database import Database,money
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt6.QtWidgets import QApplication,QMessageBox
from app import PocketAtlas
APP=QApplication.instance() or QApplication([])


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.db=Database(Path(self.temp.name)/'test.db')
    def tearDown(self):
        self.db.close();self.temp.cleanup()
    def seed(self):
        a=self.db.save_account('Cash','Cash','1000');e=self.db.save_category('Food');i=self.db.save_category('Salary','Income')
        t=self.db.save_transaction('Lunch',a,e,'120.35','2026-10-22');self.db.save_transaction('Income',a,i,'500','2026-10-22')
        b=self.db.save_budget(e,'2026-10','2000');return a,e,i,t,b
    def test_balances_budget_crud_and_delete_protection(self):
        a,e,i,t,b=self.seed();self.assertEqual(self.db.accounts()[0]['balance'],137965);self.assertEqual(self.db.budgets()[0]['spent'],12035)
        self.db.save_transaction('Dinner',a,e,'150','2026-10-22','New note',t);self.assertEqual(self.db.budgets()[0]['spent'],15000)
        with self.assertRaises(ValueError):self.db.delete('accounts',a)
        with self.assertRaises(ValueError):self.db.save_category('Food','Income',e)
        self.db.save_budget(e,'2026-10',2500,b);self.assertEqual(self.db.get('budgets',b)['amount'],250000)
        self.db.delete('transactions',t);self.db.delete('budgets',b);self.db.delete('categories',e)
        self.assertEqual(self.db.accounts()[0]['balance'],150000)
    def test_validation_and_filtering(self):
        a,e,i,t,b=self.seed()
        for v in ['NaN','Infinity',-1,0,'bad']:
            with self.subTest(v=v),self.assertRaises(ValueError):money(v)
        self.assertEqual(money('0.105'),11)
        with self.assertRaises(ValueError):self.db.save_transaction('Bad',999,e,20,'2026-10-22')
        with self.assertRaises(ValueError):self.db.save_budget(i,'2026-10',20)
        with self.assertRaises(ValueError):self.db.save_budget(e,'2026-10',20)
        with self.assertRaises(ValueError):self.db.transactions(start='2026-10-22',end='2026-10-01')
        self.assertEqual(len(self.db.transactions(kind='Expense',start='2026-10-01',end='2026-10-31')),1)
        self.assertEqual(self.db.transactions("' OR 1=1 --"),[])
    def test_json_import_roundtrip_deduplication_and_atomic_failure(self):
        self.seed();payload=self.db.export();other=Database(Path(self.temp.name)/'other.db')
        try:
            self.assertEqual(other.import_data(json.loads(json.dumps(payload))),6)
            self.assertEqual(other.import_data(payload),0)
            self.assertEqual(other.accounts()[0]['balance'],137965)
            self.assertEqual(other.budgets()[0]['spent'],12035)
        finally:other.close()
        bad=json.loads(json.dumps(payload));bad['transactions'][0]['amount']='invalid'
        empty=Database(Path(self.temp.name)/'empty.db')
        try:
            with self.assertRaises(ValueError):empty.import_data(bad)
            self.assertEqual(empty.accounts(),[]);self.assertEqual(empty.categories(),[])
        finally:empty.close()


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.errors=[]
        self.hook=patch.object(sys,'excepthook',side_effect=lambda t,e,b:self.errors.append(str(e)));self.hook.start()
        self.db=Database(Path(self.temp.name)/'test.db');self.w=PocketAtlas(self.db);self.w.show();APP.processEvents()
    def tearDown(self):
        self.w.dirty=False;self.w.close();APP.processEvents();self.hook.stop();self.temp.cleanup();self.assertEqual(self.errors,[])
    def test_menu_screens_layout_and_demo(self):
        w=self.w;w.load_demo();self.assertGreaterEqual(len(w.menuBar().actions()),3);self.assertEqual(w.stack.count(),6)
        for width,height in [(1120,780),(1420,930)]:
            w.resize(width,height)
            for index in range(6):
                self.assertTrue(w.navigate(index));APP.processEvents();scroll=w.stack.currentWidget()
                self.assertLessEqual(scroll.widget().width(),scroll.viewport().width(),w.PAGES[index])
        self.assertEqual(len(self.db.transactions()),3)
    def test_forms_crud_and_unsaved_protection(self):
        w=self.w;w.navigate(2);w.a_name.setText('My wallet');self.assertTrue(w.save_record('accounts'));a=w.ids['accounts']
        w.navigate(3);w.c_name.setText('Food');self.assertTrue(w.save_record('categories'));c=w.ids['categories']
        w.new_transaction();w.t_title.setText('Lunch');w.t_account.setCurrentIndex(w.t_account.findData(a));w.t_category.setCurrentIndex(w.t_category.findData(c));w.t_amount.setValue(100)
        self.assertTrue(w.save_record('transactions'));key=w.ids['transactions'];w.t_amount.setValue(125);self.assertTrue(w.save_record('transactions'))
        self.assertEqual(self.db.get('transactions',key)['amount'],12500)
        w.t_title.setText('Unsaved')
        with patch('app.QMessageBox.question',return_value=QMessageBox.StandardButton.Cancel):self.assertFalse(w.navigate(0))
        self.assertEqual(w.current_page,1)
        with patch('app.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):w.delete_record('transactions')
        self.assertEqual(self.db.transactions(),[])
    def test_import_export_and_filtered_csv(self):
        w=self.w;w.load_demo();path=Path(self.temp.name)/'export.json'
        with patch('app.QFileDialog.getSaveFileName',return_value=(str(path),'')):w.export_json()
        before=len(self.db.transactions())
        with patch('app.QFileDialog.getOpenFileName',return_value=(str(path),'')):w.import_json()
        self.assertEqual(len(self.db.transactions()),before);self.assertIn('0 new records',w.notice.text())
        w.report_kind.setCurrentText('Expense');csv=Path(self.temp.name)/'report.csv'
        with patch('app.QFileDialog.getSaveFileName',return_value=(str(csv),'')):w.export_csv()
        self.assertIn('Demo · Lunch',csv.read_text(encoding='utf-8-sig'));self.assertNotIn('Demo · Pocket money',csv.read_text(encoding='utf-8-sig'))


if __name__=='__main__':unittest.main()
