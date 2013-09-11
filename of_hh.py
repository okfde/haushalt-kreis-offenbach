# all the imports
import json
import sqlite3
from flask import Flask, request, session, g, redirect,url_for, \
  abort, render_template, flash, Response
from contextlib import closing
import re

# configuration

# create our little application :)
app = Flask(__name__)
# app.config.from_object(__name__)
app.config['FREEZER_RELATIVE_URLS'] = True
app.config['DEBUG'] = True
app.config['DATABASE'] = 'HH-Kreis-Offenbach.sqlite'

def connect_db():
  return sqlite3.connect(app.config['DATABASE'])

def init_db():
  with closing(connect_db()) as db:
    with app.open_resource('schema.sql') as f:
      db.cursor().executescript(f.read())
      db.commit()

def query_db(query, args=(), one=False):
  cur = g.db.execute(query, args)
  rv = [dict((cur.description[idx][0], value)
    for idx, value in enumerate(row)) for row in cur.fetchall()]
  return (rv[0] if rv else None) if one else rv

def tremapCalc(t):
  t['show'] = "true"
  if t['anteil'] <= 10:
    t['color'] = "#e3d6d6"
    t['show'] = "false"
  elif t['anteil'] > 10 and t['anteil'] < 20:
    t['color'] = "#cfbaba"
  elif t['anteil'] > 20 and t['anteil'] < 40:
    t['color'] = "#b69595"
  elif t['anteil'] > 40 and t['anteil'] < 60:
    t['color'] = "#9c7070"
  elif t['anteil'] > 60 and t['anteil'] < 80:
    t['color'] = "#834b4b"
  elif t['anteil'] > 80:
    t['color'] = "#4F0000"
  return t

@app.before_request
def before_request():
  """Make sure we are connected to the database each request."""
  g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
  """Closes the database again at the end of the request."""
  if hasattr(g, 'db'):
    g.db.close()

@app.template_filter()
def number_trunc(num):
  return "%.*f" % (0, num)

@app.template_filter()
def number_anteil(num):
  return "%.*f" % (2, num)

def get_years():
  years = query_db('select jahr from haushalt group by jahr')
  return years

def get_sektoren():
  sektoren =  query_db('select * from fachdienste order by fachdienst ASC')
  return sektoren

@app.template_filter()
def number_format(value, tsep='.', dsep=','):
  s = unicode(value)
  cnt = 0
  numchars = dsep + '0123456789'
  ls = len(s)
  while cnt < ls and s[cnt] not in numchars:
    cnt += 1
  lhs = s[:cnt]
  s = s[cnt:]
  if not dsep:
    cnt = -1
  else:
    cnt = s.rfind(dsep)
  if cnt > 0:
    rhs = dsep + s[cnt+1:]
    s = s[:cnt]
  else:
    rhs = ''
  splt = ''
  while s != '':
    splt = s[-3:] + tsep + splt
    s = s[:-3]
  return lhs + splt[:-1] + rhs

@app.route('/')
def index():
  return redirect('/gesamt/A/2012/')

@app.route('/gesamt/<flow>/<year>/')
def show_gesamt(flow, year):
  info = query_db('select sum(euro) as main_value, jahr, E_A from haushalt where haushalt.jahr = ? and haushalt.E_A = "A"', [year], one=True)
  total = info['main_value']
  info['flow'] = flow

  vorjahr = int(year)-1
  einnahmen = query_db('select jahr, sum(euro) as main_value from haushalt where jahr = ? and E_A = "E"', [year], one=True)
  entries = []
  for t in query_db('select jahr, sum(euro) as main_value, produktgruppe, haushalt.produktbereich, haushalt.rowid as id, fachdienst as title from haushalt join fachdienste on haushalt.produktbereich = fachdienste.produktbereich where jahr = ? and E_A = ? group by fachdienst order by sum(euro) desc', [year, flow]):

    prozent = query_db('select 100 - ((select sum(euro) from haushalt where jahr = ? and E_A = ? and produktbereich = hh.produktbereich)) * 100 / sum(euro) as prozent from haushalt as hh where jahr = ? and E_A = ? and produktbereich = ?', [vorjahr, flow, year, flow, t['produktbereich']], one=True)
    t['prozent'] = prozent['prozent']
    t['anteil'] = (float(t['main_value']) / total) * 100
    t = tremapCalc(t)
    entries.append(t)

    years_agg = query_db('select jahr, sum( case when produktbereich = 20 THEN euro else 0 end) as finanzen, sum( case when produktbereich = 65 THEN euro else 0 end) as gebaeude, sum( case when produktbereich = 51 THEN euro else 0 end) as jugend, sum( case when produktbereich = 50 THEN euro else 0 end) as arbeitsmarkt, sum( case when produktbereich = 40 THEN euro else 0 end) as schule from haushalt where E_A = "' + flow + '" group by jahr')

  return render_template('start.html', sektoren=get_sektoren(), einnahmen=einnahmen, entries=entries, info=info, years_agg=years_agg, years=get_years())

@app.route('/produktgruppe/<flow>/<produkt>/<year>/')
def show_produktgruppe(flow, produkt, year):

  file = open('log.txt', 'a')
  input = produkt + ": " + year + " " + flow + "\n\n"
  file.write(input)
  file.close()

  info = query_db('select sum(euro) as main_value, jahr, fachdienst, haushalt.produktbereich, E_A from haushalt join fachdienste on haushalt.produktbereich = fachdienste.produktbereich where haushalt.produktbereich = ? and jahr = ? and E_A = ?', [produkt, year, flow], one=True)
  total = info['main_value']
  info['flow'] = flow

  vorjahr = int(year)-1
  einnahmen = query_db('select sum(euro) as main_value from haushalt where produktbereich = ? and jahr = ? and E_A = "E"', [produkt, year], one=True)
  entries = []
  year_query = "select jahr "

  alpha = map(chr, range(97, 123))
  i = 1
  for t in query_db('select sum(euro) as main_value, produkt, rowid as id, jahr, produktgruppe, produktgruppe_bez as title from haushalt where produktbereich = ? and jahr = ? and E_A = ? group by produktgruppe_bez order by sum(euro) desc', [produkt, year, flow]):

    prozent = query_db('select 100 - ((select sum(euro) from haushalt where jahr = ? and E_A = ? and produktgruppe = hh.produktgruppe)) * 100 / sum(euro) as prozent from haushalt as hh where jahr = ? and E_A = ? and produktgruppe = ?', [vorjahr, flow, year, flow, t['produktgruppe']], one=True)
    t['prozent'] = prozent['prozent']

    year_query+= ", sum( case when produkt = '" + t['produkt'] + "' THEN euro else 0 end) as produkt" + str(i) + " "

    if t['main_value'] != 0 or total != 0:
      t['anteil'] = (float(t['main_value']) / total) * 100
      t = tremapCalc(t)
    entries.append(t)
    i +=1
  info['count'] = i

  years_agg = query_db(year_query + ' from haushalt where produktbereich = "' + produkt + '" and E_A = "' + flow + '" group by jahr')

  return render_template('sektor.html', years_agg=years_agg, alphabet=alpha, sektoren=get_sektoren(), entries=entries, info=info, einnahmen=einnahmen, years=get_years())
  #return str(year_query)

@app.route('/haushaltsposition/<flow>/<produkt>/<year>/')
def show_haushaltsposition(flow, produkt, year):

  info = query_db('select sum(euro) as main_value, jahr, produkt, fachdienst, haushalt.produktgruppe_bez, E_A from haushalt join fachdienste on haushalt.produktbereich = fachdienste.produktbereich where haushalt.produkt = ? and jahr = ? and E_A = ?', [produkt, year, flow], one=True)
  total = info['main_value']
  info['flow'] = flow

  vorjahr = int(year)-1
  einnahmen = query_db('select sum(euro) as main_value from haushalt where produkt = ? and jahr = ? and E_A = "E"', [produkt, year], one=True)

  entries = []
  for t in query_db('select sum(euro) as main_value, produkt, rowid as id, jahr, produktgruppe, haushaltsposition as title from haushalt where produkt = ? and jahr = ? and E_A = ? group by haushaltsposition order by sum(euro) desc', [produkt, year, flow]):

    prozent = query_db('select 100 - ((select sum(euro) from haushalt where jahr = ? and E_A = ? and haushaltsposition = hh.haushaltsposition and produkt = hh.produkt)) * 100 / sum(euro) as prozent from haushalt as hh where jahr = ? and E_A = ? and haushaltsposition = ? and produkt = ?', [vorjahr, flow, year, flow, t['title'], produkt], one=True)
    t['prozent'] = prozent['prozent']

    if t['main_value'] != 0 or total != 0:
      t['anteil'] = (float(t['main_value']) / total ) * 100
      t = tremapCalc(t)
    entries.append(t)

  return render_template('haushaltsposition.html', sektoren=get_sektoren(), entries=entries, info=info, einnahmen=einnahmen, years=get_years())
  
@app.route('/hinweis/')
def show_hinweis(): 
  return render_template('hinweis.html')

# @app.errorhandler(404)
# def page_not_found(error):
#     return render_template('page_not_found.html'), 404

if __name__ == '__main__':
        app.run()
