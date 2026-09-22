#!/usr/bin/env python3
"""Controle en lecture seule des stations autour de Montpellier.

Execute le client et les calculs deployes dans le conteneur Home Assistant :
    docker exec -i homeassistant python3 -u - < outils/tester_stations.py

Aucune station ajoutee, aucun appel au recorder, aucun fichier de HA modifie.
Les lacunes de la source sont rapportees separement des echecs de calcul.
"""
import asyncio,json,math,statistics,sys
from datetime import date,timedelta
sys.path.insert(0,'/config')
import aiohttp
from homeassistant.util import dt as dt_util
from custom_components.hubeau.api import ApiHubEau
from custom_components.hubeau import statistiques as stats

async def main():
    resultats=[]
    async with aiohttp.ClientSession() as session:
        api=ApiHubEau(session)
        stations=await api.stations_proches(3.88,43.61,25)
        for station in stations:
            code=station['code_station']; now=dt_util.utcnow()
            r={'code':code,'station':station['libelle_station']}
            try:
                h=await api.serie_recente(code,'H',heures=168)
                await asyncio.sleep(1)
                q=await api.derniere_mesure(code,'Q')
                await asyncio.sleep(1)
                q12=await api.serie_recente(code,'Q',heures=12) if q else []
                resume=stats.resume_sept_jours(h,now)
                points={d:v for d,v in h if now-timedelta(days=7)<=d<=now}
                assert all(math.isfinite(v) for v in points.values())
                if points:
                    valeurs=list(points.values())
                    assert resume['minimum_7_jours']==round(min(valeurs),4)
                    assert resume['maximum_7_jours']==round(max(valeurs),4)
                    assert resume['moyenne_7_jours']==round(statistics.mean(valeurs),4)
                else: assert resume=={}
                h12=[(d,v) for d,v in h if d>=now-timedelta(hours=12)]
                r.update(resume)
                r.update({'hauteur':h[-1][1] if h else None,'debit':q['valeur'] if q else None,'age_h_minutes':round((now-h[-1][0]).total_seconds()/60,1) if h else None,'age_q_minutes':round((now-q['date']).total_seconds()/60,1) if q else None,'figee_h':stats.est_figee(h12),'figee_q':stats.est_figee(q12),'incoherente':stats.hauteur_incoherente(h[-1][1] if h else None,q['valeur'] if q else None),'resume_verifie':True})
                if code in ('Y321002101','Y311000301','Y314001001','Y320003001'):
                    r['references']={}
                    for grandeur in ('HIXnJ','QmnJ'):
                        serie=await api.serie_journaliere(code,grandeur,date(now.year-30,1,1),now.date())
                        ref=stats.calculer(serie)
                        if ref:
                            valeurs=[v for _,v in serie]
                            assert ref.minimum==round(min(valeurs),3)
                            assert ref.maximum==round(max(valeurs),3)
                            assert ref.moyenne==round(statistics.mean(valeurs),3)
                            assert list(ref.percentiles.values())==sorted(ref.percentiles.values())
                        r['references'][grandeur]={'jours':len(serie),'disponible':ref is not None}
                r['statut']='OK'
            except Exception as e:
                r['statut']='ECHEC';r['erreur']=f'{type(e).__name__}: {e}'
            resultats.append(r)
            print(json.dumps(r,ensure_ascii=False),flush=True)
            await asyncio.sleep(1)
    print('RESULTATS_JSON='+json.dumps(resultats,ensure_ascii=False),flush=True)
    if any(r['statut'] == 'ECHEC' for r in resultats):
        raise SystemExit(1)
asyncio.run(main())
