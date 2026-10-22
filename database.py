"""Validated SQLite ledger. Money is stored as integer paise, never floats."""
import json
import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4, UUID

TYPES = ('Bank', 'Cash', 'Wallet', 'Savings')
KINDS = ('Expense', 'Income')


def title(value, limit=120):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
        raise ValueError(f'Enter text between 1 and {limit} characters.')
    return value.strip()


def money(value, allow_zero=False):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > 10000000 or (not allow_zero and amount == 0):
            raise ValueError()
        paise = int((amount*100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        if not allow_zero and paise == 0:
            raise ValueError()
        return paise
    except (ValueError, InvalidOperation, TypeError):
        raise ValueError('Enter a valid amount up to ₹10,000,000'+(' (zero allowed).' if allow_zero else ', greater than zero.')) from None


def day(value):
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        raise ValueError('Choose a valid date.') from None


class Database:
    def __init__(self, path=None):
        default = Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'PocketAtlas'/'pocket-atlas.sqlite3' if getattr(sys,'frozen',False) else Path(__file__).resolve().parent/'data'/'pocket-atlas.sqlite3'
        self.path = Path(path) if path else default
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.importing = False
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY,uid TEXT NOT NULL UNIQUE,name TEXT NOT NULL UNIQUE COLLATE NOCASE,type TEXT NOT NULL,opening INTEGER NOT NULL CHECK(opening>=0));
        CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY,uid TEXT NOT NULL UNIQUE,name TEXT NOT NULL UNIQUE COLLATE NOCASE,kind TEXT NOT NULL CHECK(kind IN ('Expense','Income')));
        CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY,uid TEXT NOT NULL UNIQUE,title TEXT NOT NULL,account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,amount INTEGER NOT NULL CHECK(amount>0),date TEXT NOT NULL,note TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS budgets(id INTEGER PRIMARY KEY,uid TEXT NOT NULL UNIQUE,category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,month TEXT NOT NULL,amount INTEGER NOT NULL CHECK(amount>0),UNIQUE(category_id,month));
        ''')

    @contextmanager
    def transaction(self):
        if self.importing:
            yield
        else:
            with self.db:
                yield

    def get(self, table, key):
        if table not in ('accounts', 'categories', 'transactions', 'budgets'):
            raise ValueError('Unknown table.')
        row = self.db.execute(f'SELECT * FROM {table} WHERE id=?', (key,)).fetchone()
        return dict(row) if row else None

    def exists(self, table, key):
        if not self.get(table, key):
            raise ValueError('The selected record no longer exists.')

    def uid(self, value=None):
        try:
            return str(UUID(value)) if value else str(uuid4())
        except (ValueError, TypeError, AttributeError):
            raise ValueError('Invalid record identifier in import.') from None

    def accounts(self):
        return [dict(r) for r in self.db.execute('''SELECT a.*,a.opening+coalesce(sum(CASE WHEN c.kind='Income' THEN t.amount ELSE -t.amount END),0) AS balance
            FROM accounts a LEFT JOIN transactions t ON t.account_id=a.id LEFT JOIN categories c ON c.id=t.category_id GROUP BY a.id ORDER BY a.name''')]

    def categories(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM categories ORDER BY kind,name')]

    def save_account(self, name, type='Bank', opening='0', key=None, uid=None):
        name, amount = title(name, 60), money(opening, True)
        if type not in TYPES:
            raise ValueError('Select a valid account type.')
        if key is not None:
            self.exists('accounts', key)
        try:
            with self.transaction():
                if key is None:
                    return self.db.execute('INSERT INTO accounts(uid,name,type,opening) VALUES(?,?,?,?)', (self.uid(uid), name, type, amount)).lastrowid
                self.db.execute('UPDATE accounts SET name=?,type=?,opening=? WHERE id=?', (name, type, amount, key))
                return key
        except sqlite3.IntegrityError:
            raise ValueError('An account with that name or identifier already exists.') from None

    def save_category(self, name, kind='Expense', key=None, uid=None):
        name = title(name, 60)
        if kind not in KINDS:
            raise ValueError('Choose Income or Expense.')
        if key is not None:
            self.exists('categories', key)
            if self.get('categories', key)['kind'] != kind and (self.db.execute('SELECT 1 FROM transactions WHERE category_id=?', (key,)).fetchone() or self.db.execute('SELECT 1 FROM budgets WHERE category_id=?', (key,)).fetchone()):
                raise ValueError('A category used by transactions or budgets cannot switch between Income and Expense.')
        try:
            with self.transaction():
                if key is None:
                    return self.db.execute('INSERT INTO categories(uid,name,kind) VALUES(?,?,?)', (self.uid(uid), name, kind)).lastrowid
                self.db.execute('UPDATE categories SET name=?,kind=? WHERE id=?', (name, kind, key))
                return key
        except sqlite3.IntegrityError:
            raise ValueError('A category with that name or identifier already exists.') from None

    def transactions(self, query='', start=None, end=None, kind='All types', account=None):
        if start:
            start = day(start)
        if end:
            end = day(end)
        if start and end and start > end:
            raise ValueError('The start date must be before the end date.')
        sql = '''SELECT t.*,a.name AS account,c.name AS category,c.kind FROM transactions t
            JOIN accounts a ON a.id=t.account_id JOIN categories c ON c.id=t.category_id WHERE
            instr(lower(t.title || ' ' || t.note || ' ' || c.name),lower(?))>0 AND
            (? IS NULL OR t.date>=?) AND (? IS NULL OR t.date<=?) AND
            (?='All types' OR c.kind=?) AND (? IS NULL OR t.account_id=?) ORDER BY t.date DESC,t.id DESC'''
        return [dict(r) for r in self.db.execute(sql, (query,start,start,end,end,kind,kind,account,account))]

    def save_transaction(self, name, account, category, amount, date, note='', key=None, uid=None):
        name, amount, date = title(name), money(amount), day(date)
        if not isinstance(note, str) or len(note)>5000:
            raise ValueError('Notes must be text of at most 5,000 characters.')
        self.exists('accounts', account)
        self.exists('categories', category)
        if key is not None:
            self.exists('transactions', key)
        with self.transaction():
            if key is None:
                return self.db.execute('INSERT INTO transactions(uid,title,account_id,category_id,amount,date,note) VALUES(?,?,?,?,?,?,?)', (self.uid(uid),name,account,category,amount,date,note.strip())).lastrowid
            self.db.execute('UPDATE transactions SET title=?,account_id=?,category_id=?,amount=?,date=?,note=? WHERE id=?', (name,account,category,amount,date,note.strip(),key))
            return key

    def budgets(self):
        return [dict(r) for r in self.db.execute('''SELECT b.*,c.name AS category,
            coalesce((SELECT sum(t.amount) FROM transactions t WHERE t.category_id=b.category_id AND substr(t.date,1,7)=b.month),0) AS spent
            FROM budgets b JOIN categories c ON c.id=b.category_id ORDER BY b.month DESC,c.name''')]

    def save_budget(self, category, month, amount, key=None, uid=None):
        self.exists('categories', category)
        if self.get('categories',category)['kind']!='Expense':
            raise ValueError('Budgets apply to expense categories.')
        day(str(month)+'-01')
        amount = money(amount)
        if key is not None:
            self.exists('budgets', key)
        try:
            with self.transaction():
                if key is None:
                    return self.db.execute('INSERT INTO budgets(uid,category_id,month,amount) VALUES(?,?,?,?)', (self.uid(uid),category,month,amount)).lastrowid
                self.db.execute('UPDATE budgets SET category_id=?,month=?,amount=? WHERE id=?', (category,month,amount,key))
                return key
        except sqlite3.IntegrityError:
            raise ValueError('That category already has a budget for this month.') from None

    def delete(self, table, key):
        self.exists(table, key)
        try:
            with self.transaction():
                self.db.execute(f'DELETE FROM {table} WHERE id=?', (key,))
        except sqlite3.IntegrityError:
            raise ValueError('This record is still used by transactions or budgets. Remove or reassign those first.') from None

    def export(self):
        accounts, categories = self.accounts(), self.categories()
        amap, cmap = {a['id']:a['uid'] for a in accounts}, {c['id']:c['uid'] for c in categories}
        return dict(format='pocket-atlas-v1',
            accounts=[dict(uid=a['uid'],name=a['name'],type=a['type'],opening=str(Decimal(a['opening'])/100)) for a in accounts],
            categories=[dict(uid=c['uid'],name=c['name'],kind=c['kind']) for c in categories],
            transactions=[dict(uid=t['uid'],title=t['title'],account_uid=amap[t['account_id']],category_uid=cmap[t['category_id']],amount=str(Decimal(t['amount'])/100),date=t['date'],note=t['note']) for t in self.transactions()],
            budgets=[dict(uid=b['uid'],category_uid=cmap[b['category_id']],month=b['month'],amount=str(Decimal(b['amount'])/100)) for b in self.budgets()])

    def import_data(self, payload):
        if not isinstance(payload,dict) or payload.get('format')!='pocket-atlas-v1':
            raise ValueError('Choose a Pocket Atlas JSON export (pocket-atlas-v1).')
        for name in ('accounts','categories','transactions','budgets'):
            if not isinstance(payload.get(name),list) or len(payload[name])>50000 or any(not isinstance(r,dict) for r in payload[name]):
                raise ValueError('The import contains an invalid or oversized record list.')
        count = 0
        try:
            with self.db:
                self.importing=True
                for table in ('accounts','categories','transactions','budgets'):
                    for record in payload[table]:
                        uid=self.uid(record.get('uid'))
                        if not record.get('uid'):
                            raise ValueError('Every imported record needs an identifier.')
                        if self.db.execute(f'SELECT 1 FROM {table} WHERE uid=?',(uid,)).fetchone():
                            continue
                        def reference(ref_table, ref_uid):
                            row=self.db.execute(f'SELECT id FROM {ref_table} WHERE uid=?',(self.uid(ref_uid),)).fetchone()
                            if not row:
                                raise ValueError('Import refers to an account or category that is missing.')
                            return row['id']
                        if table=='accounts':
                            self.save_account(record.get('name'),record.get('type'),record.get('opening'),uid=uid)
                        elif table=='categories':
                            self.save_category(record.get('name'),record.get('kind'),uid=uid)
                        elif table=='transactions':
                            self.save_transaction(record.get('title'),reference('accounts',record.get('account_uid')),reference('categories',record.get('category_uid')),record.get('amount'),record.get('date'),record.get('note',''),uid=uid)
                        else:
                            self.save_budget(reference('categories',record.get('category_uid')),record.get('month'),record.get('amount'),uid=uid)
                        count+=1
            return count
        except (KeyError,TypeError,sqlite3.Error) as exc:
            raise ValueError('Invalid import; no changes were applied. '+str(exc)) from exc
        finally:
            self.importing=False

    def close(self):
        self.db.close()
