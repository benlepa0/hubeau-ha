/*!
 * Carte Hub'Eau pour Home Assistant.
 *
 * Montre l'etat d'une station hydrometrique : le niveau d'eau, monte a la
 * hauteur que lui donne son rang dans trente ans de chronique, et le courant,
 * dont la vitesse suit le debit.
 *
 * Le parti pris tient en une idee : une riviere ne se lit pas sur une echelle
 * lineaire. Sur le Lez, la mediane vaut 0,44 m et le maximum 4,40 ; en etiage,
 * une echelle proportionnelle ecraserait l'eau sur un filet invisible au bas
 * du cadre. L'echelle verticale suit donc les *percentiles* : chaque repere
 * est place a une position fixe, et l'eau monte selon son rang. La moitie
 * basse du cadre couvre ainsi la moitie du temps, ce qui rend l'etiage aussi
 * lisible que la crue.
 *
 * Aucune dependance, aucune compilation : un element personnalise et du SVG.
 */

const VERSION = "0.4.1";

/* Reperes de l'echelle : percentile -> position verticale, de 0 en bas a 1
 * en haut. Les valeurs sont resserrees vers le haut parce que les crues sont
 * rares : les derniers pour cent du temps occupent le quart superieur. */
const ECHELLE = [
  [0, 0.00], [5, 0.08], [25, 0.20], [50, 0.34], [75, 0.48],
  [90, 0.60], [95, 0.70], [99, 0.84], [99.9, 0.93], [100, 1.00],
];

const REGIMES = {
  etiage_severe: { libelle: "Étiage sévère", couleur: "#78909C", eau: "#90A4AE" },
  etiage:        { libelle: "Étiage",        couleur: "#4FC3F7", eau: "#4FC3F7" },
  normal:        { libelle: "Normal",        couleur: "#29B6F6", eau: "#2196F3" },
  soutenu:       { libelle: "Soutenu",       couleur: "#26A69A", eau: "#1E88E5" },
  fort:          { libelle: "Fort",          couleur: "#FFB300", eau: "#1976D2" },
  crue:          { libelle: "Crue",          couleur: "#FB8C00", eau: "#F57C00" },
  crue_majeure:  { libelle: "Crue majeure",  couleur: "#E53935", eau: "#D32F2F" },
  indisponible:  { libelle: "Indisponible",  couleur: "#9E9E9E", eau: "#BDBDBD" },
};

const position = (rang) => {
  if (rang == null || Number.isNaN(rang)) return 0;
  const r = Math.max(0, Math.min(100, rang));
  for (let i = 1; i < ECHELLE.length; i++) {
    const [p1, y1] = ECHELLE[i - 1], [p2, y2] = ECHELLE[i];
    if (r <= p2) return y1 + ((r - p1) / (p2 - p1)) * (y2 - y1);
  }
  return 1;
};

const nombre = (v, d = 2) =>
  v == null || v === "" || Number.isNaN(Number(v))
    ? "—" : Number(v).toLocaleString("fr-FR",
        { minimumFractionDigits: d, maximumFractionDigits: d });

class CarteHubEau extends HTMLElement {
  static getStubConfig(hass) {
    const h = Object.keys(hass.states).find((e) => e.endsWith("_hauteur_d_eau"));
    return { type: "custom:hubeau-card", hauteur: h || "" };
  }

  setConfig(config) {
    if (!config.hauteur && !config.entity) {
      throw new Error("Indiquez au moins « hauteur » (le capteur de hauteur d'eau).");
    }
    const base = (config.hauteur || config.entity).replace(/_hauteur_d_eau$/, "");
    /* Les autres capteurs de la station se deduisent du premier : ils
     * partagent le meme prefixe. On laisse la possibilite de les nommer un a
     * un, pour les installations ou les identifiants auraient ete renommes. */
    this._cfg = {
      titre: config.title ?? null,
      hauteur: config.hauteur || config.entity,
      debit: config.debit || `${base}_debit`,
      regime: config.regime || `${base}_regime`,
      rang: config.rang || `${base}_rang_sur_la_chronique`,
      tendance: config.tendance || `${base}_tendance`,
      age: config.age || `${base}_age_de_la_mesure`,
      derniere: config.derniere || `${base}_derniere_mesure`,
      animations: config.animations !== false,
    };
    this._construire();
  }

  set hass(hass) {
    this._hass = hass;
    this._rendre();
    this._afficherSeptJours();
  }

  getCardSize() { return 5; }

  /* Le bandeau lit les mesures des sept derniers jours, sans consulter le recorder. */
  _afficherSeptJours() {
    const zone = this._racine?.querySelector(".references");
    if (!zone) return;
    const attrs = this._hass?.states[this._cfg.hauteur]?.attributes || {};
    const valeur = (v) => v == null || v === "" || !Number.isFinite(Number(v))
      ? null : Number(v);
    const mini = valeur(attrs.minimum_7_jours);
    const moyenne = valeur(attrs.moyenne_7_jours);
    const maxi = valeur(attrs.maximum_7_jours);
    zone.classList.remove("vide");
    const f = (v) => v == null ? "—" : `${nombre(v, 2)} m`;
    this._racine.querySelector("#r-min").textContent = f(mini);
    this._racine.querySelector("#r-moy").textContent = f(moyenne);
    this._racine.querySelector("#r-max").textContent = f(maxi);
    zone.title = "7 derniers jours : minimum, moyenne arithmétique et maximum des mesures disponibles";
    if (attrs.debut_mesures_7_jours && attrs.fin_mesures_7_jours) {
      zone.title += `, du ${attrs.debut_mesures_7_jours} au ${attrs.fin_mesures_7_jours}`;
    }
  }

  /* -- construction, une seule fois ------------------------------------- */

  _construire() {
    if (this._racine) return;
    this._racine = this.attachShadow({ mode: "open" });
    this._racine.innerHTML = `
      <style>
        :host { display: block; }
        ha-card {
          overflow: hidden; padding: 0;
          --eau: #2196F3; --accent: #2196F3;
        }
        .entete {
          display: flex; align-items: baseline; gap: 10px;
          padding: 14px 16px 10px;
        }
        .titre { font-size: .98rem; font-weight: 600; flex: 1; line-height: 1.25;
                 display: -webkit-box; -webkit-line-clamp: 2;
                 -webkit-box-orient: vertical; overflow: hidden; }
        .regime {
          font-size: .72rem; font-weight: 700; letter-spacing: .04em;
          text-transform: uppercase; padding: 3px 9px; border-radius: 999px;
          color: #fff; background: var(--accent); white-space: nowrap;
        }
        .scene { position: relative; height: 215px; overflow: hidden; }

        /* La masse d'eau : un bloc pose au fond, dont la hauteur suit le rang. */
        .eau {
          position: absolute; left: 0; right: 0; bottom: 0;
          background: linear-gradient(180deg,
                      color-mix(in srgb, var(--eau) 92%, #fff) 0%,
                      var(--eau) 45%,
                      color-mix(in srgb, var(--eau) 78%, #000) 100%);
          transition: height 1.2s cubic-bezier(.4,0,.2,1);
          overflow: hidden;
        }
        /* La surface distincte laisse les vagues deborder au-dessus de l'eau. */
        .surface { position: absolute; left: 0; right: 0; height: 20px;
                   overflow: hidden; pointer-events: none;
                   transition: bottom 1.2s cubic-bezier(.4,0,.2,1); }
        .surface svg { position: absolute; top: 0; left: 0;
                       width: 200%; height: 20px; }

        /* Deux sinusoides, l'une glissant a contresens de l'autre. Rien de
           plus : une troisieme onde puis une crete blanche avaient ete
           essayees, et alourdissaient le trace sans le rendre plus vivant. */
        /* Nommees "onde" et non "v" : la classe v designe deja les valeurs
           chiffrees du pied de carte, qui heritaient donc du glissement des
           vagues et defilaient vers la gauche en boucle, sans raison
           apparente. */
        .onde { animation: glisse var(--t, 9s) linear infinite; }
        .onde2 { animation-duration: var(--t2, 13s); animation-direction: reverse; }
        @keyframes glisse { to { transform: translateX(-50%); } }

        @media (prefers-reduced-motion: reduce) {
          .onde { animation: none; }
        }
        :host([sans-animation]) .onde { animation: none; }

        .reperes { position: absolute; inset: 0; pointer-events: none; }
        .repere { position: absolute; left: 0; right: 0; display: flex;
                  align-items: center; gap: 6px; }
        .repere .trait { flex: 1; border-top: 1px dashed
                         var(--divider-color, rgba(255,255,255,.18)); }
        .repere .etiq { font-size: .62rem; opacity: .65; padding-right: 10px;
                        font-variant-numeric: tabular-nums; }

        /* En haut, et non en bas : l'eau monte, et un texte place en bas de
           cadre finissait noye des que le niveau depassait l'etiage. */
        .valeurs { position: absolute; left: 16px; top: 14px; right: 118px; }
        /* Les zones cliquables ouvrent la fiche de l'entite, d'ou l'on accede
           a l'historique et aux statistiques long terme. */
        .cliquable { cursor: pointer; border-radius: 8px;
                     transition: background .15s; }
        .cliquable:hover { background: rgba(255,255,255,.08); }
        .cliquable:focus-visible { outline: 2px solid var(--accent);
                                   outline-offset: 2px; }
        .grande { font-size: 2.5rem; font-weight: 300; line-height: 1;
                  font-variant-numeric: tabular-nums; }
        .grande small { font-size: .9rem; opacity: .75; margin-left: 4px; }
        .lecture { font-size: .76rem; opacity: .9; margin-top: 7px;
                   line-height: 1.35;
                   display: -webkit-box; -webkit-line-clamp: 2;
                   -webkit-box-orient: vertical; overflow: hidden; }

        .pied { display: grid; grid-template-columns: repeat(3, 1fr);
                border-top: 1px solid var(--divider-color, rgba(255,255,255,.12)); }
        .references { position: relative; }
        .references::before {
          content: "7 derniers jours"; position: absolute; top: 5px; left: 0;
          right: 0; text-align: center; font-size: .58rem; opacity: .45;
          text-transform: uppercase; letter-spacing: .06em;
        }
        .references .case { padding-top: 22px; }
        .references.vide { display: none; }
        .case { padding: 9px 6px; text-align: center; }
        .case + .case { border-left: 1px solid
                        var(--divider-color, rgba(255,255,255,.12)); }
        .case .k { font-size: .6rem; text-transform: uppercase;
                   letter-spacing: .04em; opacity: .6; white-space: nowrap; }
        .case .v { font-size: .92rem; font-weight: 600; margin-top: 3px;
                   font-variant-numeric: tabular-nums; white-space: nowrap; }
        .avert { padding: 8px 16px; font-size: .74rem;
                 background: rgba(251,140,0,.14); color: var(--warning-color, #FB8C00); }
        .cache { display: none; }
      </style>
      <ha-card>
        <div class="entete">
          <div class="titre"></div>
          <div class="regime"></div>
        </div>
        <div class="scene">
          <div class="eau"></div>
          <div class="surface">
            <svg viewBox="0 0 600 20" preserveAspectRatio="none">
              <path class="onde"       opacity=".55" fill="var(--eau)"></path>
              <path class="onde onde2" opacity=".35" fill="var(--eau)"></path>
            </svg>
          </div>
          <div class="reperes"></div>
          <div class="valeurs">
            <div class="grande cliquable" data-cible="hauteur" tabindex="0"
                 role="button" title="Voir l'historique de la hauteur"></div>
            <div class="lecture"></div>
          </div>
        </div>
        <div class="avert cache"></div>
        <div class="pied">
          <div class="case cliquable" data-cible="debit" tabindex="0" role="button"
               title="Voir l'historique du débit"><div class="k">Débit</div><div class="v" id="c-debit">—</div></div>
          <div class="case"><div class="k">Tendance</div><div class="v" id="c-tend">—</div></div>
          <div class="case"><div class="k">Mesurée à</div><div class="v" id="c-age">—</div></div>
        </div>
        <div class="pied references vide">
          <div class="case"><div class="k">Minimum</div><div class="v" id="r-min">—</div></div>
          <div class="case"><div class="k">Moyenne</div><div class="v" id="r-moy">—</div></div>
          <div class="case"><div class="k">Maximum</div><div class="v" id="r-max">—</div></div>
        </div>
      </ha-card>`;

    const chemins = this._racine.querySelectorAll(".surface path");
    // Deux sinusoides, dessinees chacune sur deux periodes : un glissement de
    // moitie ramene donc exactement au motif de depart, sans saut a la
    // reprise de la boucle.
    [[10, 0], [7, 30]].forEach(([a, dec], i) => {
      chemins[i].setAttribute("d", this._onde(a, dec));
    });

    /* Ouvrir la fiche d'une entite depuis la carte.
     *
     * Home Assistant ecoute l'evenement hass-more-info sur le document ; il
     * doit donc traverser la frontiere du shadow DOM, d'ou composed a vrai.
     * Sans cela l'evenement resterait enferme dans la carte et rien ne
     * s'ouvrirait. */
    const ouvrir = (cible) => {
      const entityId = this._cfg[cible];
      if (!entityId || !this._hass?.states?.[entityId]) return;
      this.dispatchEvent(new CustomEvent("hass-more-info", {
        detail: { entityId }, bubbles: true, composed: true,
      }));
    };
    for (const el of this._racine.querySelectorAll(".cliquable")) {
      el.addEventListener("click", () => ouvrir(el.dataset.cible));
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          ouvrir(el.dataset.cible);
        }
      });
    }

    if (!this._cfg.animations) this.setAttribute("sans-animation", "");
  }

  _onde(amplitude, decalage) {
    // Le trace couvre deux periodes de 300 unites sur les 600 du cadre : un
    // glissement de moitie ramene donc exactement au motif de depart, sans
    // saut visible a la reprise de la boucle.
    let d = "";
    for (let x = 0; x <= 600; x += 5) {
      const y = amplitude + Math.sin(((x + decalage) / 300) * Math.PI * 2) * amplitude;
      d += `${x === 0 ? "M" : "L"} ${x} ${y.toFixed(2)} `;
    }
    return `${d} L 600 20 L 0 20 Z`;
  }

  /* -- mise a jour ------------------------------------------------------- */

  _rendre() {
    if (!this._hass || !this._racine) return;
    const h = this._hass.states[this._cfg.hauteur];
    const r = this._racine;

    if (!h) {
      r.querySelector(".titre").textContent = "Entité introuvable";
      r.querySelector(".lecture").textContent = this._cfg.hauteur;
      return;
    }

    const attrs = h.attributes || {};
    const etatRegime = this._hass.states[this._cfg.regime];
    const cle = etatRegime?.state || attrs.regime || "indisponible";
    const reg = REGIMES[cle] || REGIMES.indisponible;
    const rang = Number(this._hass.states[this._cfg.rang]?.state ?? attrs.rang_percentile);
    const dispo = h.state !== "unavailable" && h.state !== "unknown";

    const carte = r.querySelector("ha-card");
    carte.style.setProperty("--eau", reg.eau);
    carte.style.setProperty("--accent", reg.couleur);

    r.querySelector(".titre").textContent =
      this._cfg.titre ?? (attrs.friendly_name || "").replace(/ Hauteur d'eau$/, "");
    r.querySelector(".regime").textContent = reg.libelle;

    r.querySelector(".grande").innerHTML = dispo
      ? `${nombre(h.state, 2)}<small>m</small>`
      : `—<small>m</small>`;
    r.querySelector(".lecture").textContent = dispo
      ? (attrs.lecture || "") + (Number.isFinite(rang) ? ` · rang ${nombre(rang, 0)} %` : "")
      : "station indisponible";

    // Le niveau : la hauteur du bloc d'eau, en pourcentage du cadre. Un
    // minimum de 4 % laisse voir un fond de lit meme a l'etiage le plus bas,
    // sans quoi la carte parait vide et l'on doute qu'elle fonctionne.
    const part = dispo && Number.isFinite(rang) ? position(rang) : 0;
    const pourcent = Math.max(4, part * 100);
    r.querySelector(".eau").style.height = `${pourcent.toFixed(1)}%`;
    // La surface se pose sur le sommet de l'eau, les vagues debordant vers le
    // haut de leur pleine amplitude.
    r.querySelector(".surface").style.bottom =
      `calc(${pourcent.toFixed(1)}% - 1px)`;

    // Le courant accelere avec le debit, entre huit et une seconde et demie
    // par traversee. L'echelle est logarithmique : entre 0,2 et 200 m3/s il y
    // a trois ordres de grandeur, qu'une echelle lineaire ecraserait.
    const debit = Number(this._hass.states[this._cfg.debit]?.state);
    let duree = 8;
    if (Number.isFinite(debit) && debit > 0) {
      const t = Math.min(1, Math.max(0, (Math.log10(debit) + 1) / 3.3));
      duree = 8 - t * 6.5;
    }
    // Les vagues suivent le courant, mais de loin : une surface n'accelere
    // pas autant que la veine d'eau qui la porte.
    carte.style.setProperty("--t",  `${(7 + duree * 0.5).toFixed(2)}s`);
    carte.style.setProperty("--t2", `${(11 + duree * 0.7).toFixed(2)}s`);

    this._reperes(attrs);
    this._pied(debit);
    this._avertir(attrs);
  }

  _reperes(attrs) {
    const zone = this._racine.querySelector(".reperes");
    const med = attrs.mediane_30_ans;
    const max = attrs.maximum_connu;
    const ans = attrs.annees_de_reference;
    const cle = JSON.stringify([med, max, ans]);
    if (this._cleReperes === cle) return;
    this._cleReperes = cle;

    const lignes = [
      [50, med != null ? `médiane ${nombre(med, 2)} m` : "médiane"],
      [95, "5 % du temps"],
      [99, "1 % du temps"],
      [100, max != null ? `record ${nombre(max, 2)} m` : "record"],
    ];
    zone.innerHTML = lignes.map(([p, texte]) => {
      const bas = position(p) * 100;
      return `<div class="repere" style="bottom:${bas.toFixed(1)}%">
                <span class="trait"></span><span class="etiq">${texte}</span>
              </div>`;
    }).join("");
  }

  _pied(debit) {
    const r = this._racine;
    r.querySelector("#c-debit").textContent =
      Number.isFinite(debit) ? `${nombre(debit, 3)} m³/s` : "—";

    const t = Number(this._hass.states[this._cfg.tendance]?.state);
    r.querySelector("#c-tend").textContent = Number.isFinite(t)
      ? `${t > 0.05 ? "↑" : t < -0.05 ? "↓" : "→"} ${nombre(Math.abs(t), 1)} cm/h`
      : "—";

    // L'heure de la mesure, et non son age seul : Hub'Eau publie certaines
    // stations par lots horaires, et un « il y a 63 min » sans autre contexte
    // laisse croire que la carte a cesse de se rafraichir.
    const brut = this._hass.states[this._cfg.derniere]?.state;
    const age = Number(this._hass.states[this._cfg.age]?.state);
    const cel = r.querySelector("#c-age");
    let texte = "—";
    if (brut && !Number.isNaN(Date.parse(brut))) {
      const d = new Date(brut);
      texte = d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
      if (Number.isFinite(age)) {
        texte += age < 90 ? ` · ${Math.round(age)} min`
                          : ` · ${nombre(age / 60, 1)} h`;
      }
    } else if (Number.isFinite(age)) {
      texte = `il y a ${Math.round(age)} min`;
    }
    cel.textContent = texte;
    cel.title = Number.isFinite(age) && age > 75
      ? "Hub'Eau publie cette station par lots : le retard est normal."
      : "";
  }

  _avertir(attrs) {
    const zone = this._racine.querySelector(".avert");
    const base = this._cfg.hauteur.replace(/^sensor\./, "")
                                  .replace(/_hauteur_d_eau$/, "");
    const fige = this._hass.states[`binary_sensor.${base}_capteur_fige`]?.state === "on"
                 || attrs.capteur_fige === true;
    const vieux = this._hass.states[`binary_sensor.${base}_donnees_obsoletes`]?.state === "on";
    const message = fige
      ? "Capteur figé : la station répond mais ne mesure plus."
      : vieux ? "Données obsolètes : aucune mesure récente." : "";
    zone.textContent = message;
    zone.classList.toggle("cache", !message);
  }
}

/* Un element personnalise ne se definit qu'une fois par page. Si une version
 * precedente a deja ete chargee -- ce qui arrive quand le navigateur sert une
 * ressource depuis son cache tout en chargeant la nouvelle --, l'appel leve
 * une erreur et le reste du fichier ne s'execute pas. On previent plutot que
 * d'echouer en silence : c'est exactement le genre de panne qui donne
 * l'impression que rien n'a change. */
if (customElements.get("hubeau-card")) {
  console.warn(
    `[hubeau-card] une version est déjà chargée dans cette page ; ` +
    `la version ${VERSION} ne sera pas prise en compte. ` +
    `Rechargez en vidant le cache.`
  );
} else {
  customElements.define("hubeau-card", CarteHubEau);

  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "hubeau-card",
    name: "Hub'Eau",
    description: "Niveau et débit d'un cours d'eau, situés dans sa chronique.",
    preview: true,
  });

  console.info(
    `%c HUBEAU-CARD %c ${VERSION} `,
    "color:#fff;background:#2196F3;font-weight:700",
    "color:#2196F3;background:#fff"
  );
}
