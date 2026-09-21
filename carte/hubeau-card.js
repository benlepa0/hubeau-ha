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

const VERSION = "0.1.0";

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
      animations: config.animations !== false,
    };
    this._construire();
  }

  set hass(hass) {
    this._hass = hass;
    this._rendre();
  }

  getCardSize() { return 5; }

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
        .scene { position: relative; height: 210px; }
        svg { display: block; width: 100%; height: 100%; }

        /* Les vagues glissent lateralement ; deux couches decalees suffisent
           a donner l'illusion d'une surface qui respire. */
        .vague { animation: glisse var(--duree, 7s) linear infinite; }
        .vague2 { animation: glisse var(--duree2, 11s) linear infinite reverse; }
        @keyframes glisse { to { transform: translateX(-50%); } }

        /* Le courant : des traits qui filent dans la masse d'eau, d'autant
           plus vite que le debit est fort. */
        .courant { animation: file var(--vitesse, 6s) linear infinite; }
        @keyframes file { from { transform: translateX(-20%); }
                          to   { transform: translateX(120%); } }

        .montee { transition: transform 1.2s cubic-bezier(.4,0,.2,1); }

        @media (prefers-reduced-motion: reduce) {
          .vague, .vague2, .courant { animation: none; }
        }
        :host([sans-animation]) .vague,
        :host([sans-animation]) .vague2,
        :host([sans-animation]) .courant { animation: none; }

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
        .grande { font-size: 2.5rem; font-weight: 300; line-height: 1;
                  font-variant-numeric: tabular-nums;
                  text-shadow: 0 1px 6px rgba(0,0,0,.45); }
        .grande small { font-size: .9rem; opacity: .75; margin-left: 4px; }
        .lecture { font-size: .76rem; opacity: .9; margin-top: 7px;
                   line-height: 1.35; text-shadow: 0 1px 5px rgba(0,0,0,.5);
                   display: -webkit-box; -webkit-line-clamp: 2;
                   -webkit-box-orient: vertical; overflow: hidden; }

        .pied { display: grid; grid-template-columns: repeat(3, 1fr);
                border-top: 1px solid var(--divider-color, rgba(255,255,255,.12)); }
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
          <svg viewBox="0 0 300 210" preserveAspectRatio="none">
            <defs>
              <linearGradient id="deg" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stop-color="var(--eau)" stop-opacity=".95"/>
                <stop offset="100%" stop-color="var(--eau)" stop-opacity=".55"/>
              </linearGradient>
              <clipPath id="coupe"><rect x="0" y="0" width="300" height="210"/></clipPath>
            </defs>
            <g clip-path="url(#coupe)">
              <g class="montee" id="masse">
                <!-- Le corps part sous l'amplitude des vagues : commence a
                     zero, il les aurait entierement recouvertes. -->
                <rect id="corps" x="-300" y="14" width="900" height="420" fill="url(#deg)"/>
                <g id="courants"></g>
                <path class="vague2" id="v2" fill="var(--eau)" opacity=".45"/>
                <path class="vague"  id="v1" fill="var(--eau)"/>
                <path class="vague" id="crete" fill="none" stroke="#fff"
                      stroke-width="1.5" opacity=".5"/>
              </g>
            </g>
          </svg>
          <div class="reperes"></div>
          <div class="valeurs">
            <div class="grande"></div>
            <div class="lecture"></div>
          </div>
        </div>
        <div class="avert cache"></div>
        <div class="pied">
          <div class="case"><div class="k">Débit</div><div class="v" id="c-debit">—</div></div>
          <div class="case"><div class="k">Tendance</div><div class="v" id="c-tend">—</div></div>
          <div class="case"><div class="k">Mesure</div><div class="v" id="c-age">—</div></div>
        </div>
      </ha-card>`;

    const svg = this._racine.querySelector("svg");
    // Deux vagues sinusoidales, dessinees deux fois de suite pour que le
    // glissement de moitie boucle sans saut visible.
    svg.querySelector("#v1").setAttribute("d", this._onde(7, 0));
    svg.querySelector("#v2").setAttribute("d", this._onde(10, 55));
    // Une crete claire souligne la surface : sans elle, deux nappes de la
    // meme couleur se confondent et l'eau parait figee.
    svg.querySelector("#crete").setAttribute("d", this._onde(7, 0, true));
    const g = svg.querySelector("#courants");
    // Les filets de courant : des traits qui filent dans la masse d'eau.
    // Premiere version a 18 % d'opacite sur deux pixels et demi : invisibles.
    // Ils sont desormais plus longs, plus clairs, et decales entre eux pour
    // que le mouvement se lise sans donner l'impression d'un peigne.
    const LIGNES = [
      [24, 34, 0.30], [52, 70, 0.22], [30, 104, 0.26], [66, 138, 0.18],
      [38, 170, 0.24], [58, 206, 0.16], [28, 240, 0.22], [48, 276, 0.14],
    ];
    LIGNES.forEach(([largeur, y, opacite], i) => {
      const t = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      t.setAttribute("class", "courant");
      t.setAttribute("x", "0");
      t.setAttribute("y", y);
      t.setAttribute("width", largeur);
      t.setAttribute("height", "3");
      t.setAttribute("rx", "1.5");
      t.setAttribute("fill", "#fff");
      t.setAttribute("opacity", opacite);
      t.style.animationDelay = `${-i * 1.15}s`;
      g.appendChild(t);
    });
    if (!this._cfg.animations) this.setAttribute("sans-animation", "");
  }

  _onde(amplitude, decalage, ligneSeule = false) {
    // Une periode sur 150 unites, repetee jusqu'a 600 : la translation de
    // -50 % ramene exactement au motif de depart, sans saut visible.
    let d = "";
    for (let x = 0; x <= 600; x += 6) {
      const y = amplitude + Math.sin((x + decalage) / 150 * Math.PI * 2) * amplitude * 0.9;
      d += `${x === 0 ? "M" : "L"} ${x} ${y.toFixed(2)} `;
    }
    return ligneSeule ? d : d + `L 600 430 L 0 430 Z`;
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

    // Le niveau : on translate la masse d'eau vers le haut selon le rang.
    const hauteurCadre = 210;
    const part = dispo && Number.isFinite(rang) ? position(rang) : 0;
    const y = hauteurCadre - part * hauteurCadre;
    r.querySelector("#masse").setAttribute(
      "transform", `translate(0 ${y.toFixed(1)})`);

    // Le courant accelere avec le debit, entre huit et une seconde et demie
    // par traversee. L'echelle est logarithmique : entre 0,2 et 200 m3/s il y
    // a trois ordres de grandeur, qu'une echelle lineaire ecraserait.
    const debit = Number(this._hass.states[this._cfg.debit]?.state);
    let duree = 8;
    if (Number.isFinite(debit) && debit > 0) {
      const t = Math.min(1, Math.max(0, (Math.log10(debit) + 1) / 3.3));
      duree = 8 - t * 6.5;
    }
    carte.style.setProperty("--vitesse", `${duree.toFixed(2)}s`);
    carte.style.setProperty("--duree", `${(6 + duree * 0.4).toFixed(2)}s`);
    carte.style.setProperty("--duree2", `${(9 + duree * 0.5).toFixed(2)}s`);

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

    const age = Number(this._hass.states[this._cfg.age]?.state);
    r.querySelector("#c-age").textContent = Number.isFinite(age)
      ? (age < 90 ? `il y a ${Math.round(age)} min`
                  : `il y a ${nombre(age / 60, 1)} h`)
      : "—";
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
