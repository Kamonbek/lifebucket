#!/usr/bin/env python3
import argparse, csv, os
from datetime import date

BASE='/workspace/life-os'


def append_row(path, headers, row):
    exists = os.path.exists(path)
    with open(path, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=headers)
        if not exists:
            w.writeheader()
        w.writerow(row)


def main():
    p = argparse.ArgumentParser(description='Append one daily check-in across life-os logs')
    p.add_argument('--date', default=str(date.today()))
    p.add_argument('--wake-time', default='')
    p.add_argument('--sleep-hours', type=float, default=0)
    p.add_argument('--deep-work-hours', type=float, default=0)
    p.add_argument('--learning-hours', type=float, default=0)
    p.add_argument('--exercise', choices=['yes','no'], default='no')
    p.add_argument('--main-task-done', choices=['yes','no'], default='no')
    p.add_argument('--mood', default='')
    p.add_argument('--energy', type=float, default=0)
    p.add_argument('--notes', default='')
    p.add_argument('--income', type=float, default=0)
    p.add_argument('--income-source', default='')
    p.add_argument('--expense', type=float, default=0)
    p.add_argument('--expense-category', default='')
    p.add_argument('--currency', default='USD')
    args = p.parse_args()

    append_row(
        f'{BASE}/logs/daily_log.csv',
        ['date','wake_time','sleep_hours','deep_work_hours','learning_hours','exercise','main_task_done','mood','energy','notes'],
        {
            'date':args.date,'wake_time':args.wake_time,'sleep_hours':args.sleep_hours,'deep_work_hours':args.deep_work_hours,
            'learning_hours':args.learning_hours,'exercise':args.exercise,'main_task_done':args.main_task_done,
            'mood':args.mood,'energy':args.energy,'notes':args.notes
        }
    )

    if args.income > 0:
        append_row(
            f'{BASE}/logs/income.csv',
            ['date','source','amount','currency','note'],
            {'date':args.date,'source':args.income_source or 'other','amount':args.income,'currency':args.currency,'note':args.notes}
        )

    if args.expense > 0:
        append_row(
            f'{BASE}/logs/expenses.csv',
            ['date','category','amount','currency','note'],
            {'date':args.date,'category':args.expense_category or 'other','amount':args.expense,'currency':args.currency,'note':args.notes}
        )

    print('checkin_saved', args.date)


if __name__ == '__main__':
    main()
