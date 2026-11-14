/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
import { ApiError } from "./errors.ts";
import type { Locale } from "./i18n";

export type Worker = {role:"supervisor"|"configuration"|"project"|"run"|"command";project_id:string;run_id:string;
  heartbeat:"recent"|"stale"|"missing";activity:"busy"|"idle"|"unknown";updated_at:string|null};
export type TrackedOperation = {id:number;action:"start"|"retry"|"restart"|"cancel"|"configure"|"pause"|"resume"|"delete";
  status:"pending"|"running"|"succeeded"|"failed"|"uncertain";result:string;reason:string};
export type Capacity = {project_id:string;active_limit:number;limit:number;occupied:number;free:number;waiting_jobs:number;available:boolean;
  worker:Worker;queue:Array<{id:number;action:TrackedOperation["action"];reason:"project_limit"|"worker_unavailable"|"same_job"|"staged_change"|"dispatching"}>;
  waiting_runs:Array<{ticket_iid:number;reason:"dispatching"|"worker_unavailable"|"project_limit"|"staged_change"}>;staged_change:boolean;staged_limit:number|null;recent_operations:TrackedOperation[]};
export const currentJobStates=["working","publishing","parked-clarification","awaiting-approval","in-review","handoff-pending"] as const;
export type CapacityOverview=Capacity&{paused:boolean;job_counts:Record<typeof currentJobStates[number],number>};
const integer=(value:unknown,minimum=0):value is number=>Number.isSafeInteger(value)&&Number(value)>=minimum;
const identity=(value:unknown)=>typeof value==="string"&&/^[a-f0-9]{32}$/.test(value);
const actions=["start","retry","restart","cancel","configure","pause","resume","delete"];
function validWorker(value:unknown):value is Worker {
  const row=value as Worker;
  return !!row&&["supervisor","configuration","project","run","command"].includes(row.role)
    && typeof row.project_id==="string"&&(row.project_id===""||identity(row.project_id))&&typeof row.run_id==="string"
    && (["project","run","command"].includes(row.role)?identity(row.project_id):true)
    && (row.role==="run"?/^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$/.test(row.run_id):row.run_id==="")
    && ["recent","stale","missing"].includes(row.heartbeat)&&["busy","idle","unknown"].includes(row.activity)
    && (row.updated_at===null?row.heartbeat==="missing":typeof row.updated_at==="string"&&Number.isFinite(Date.parse(row.updated_at)))
    && (row.heartbeat==="recent"?row.activity!=="unknown":row.activity==="unknown");
}
export function readWorkers(value:unknown):{workers:Worker[]} {
  const row=value as {workers:Worker[]};
  if(!row||!Array.isArray(row.workers)||!row.workers.every(validWorker))throw new ApiError("unexpected_response");
  return row;
}
export function readCapacity(value:unknown,project:string):Capacity {
  const row=value as Capacity;
  if(!row||row.project_id!==project||!identity(row.project_id)||!integer(row.limit,1)||!integer(row.active_limit,1)||row.limit>row.active_limit||!integer(row.occupied)||!integer(row.free)
    ||row.free!==Math.max(0,row.limit-row.occupied)||!integer(row.waiting_jobs)||typeof row.available!=="boolean"
    ||!validWorker(row.worker)||row.worker.role!=="project"||row.worker.project_id!==project
    ||row.available&&(row.free===0||row.worker.heartbeat!=="recent")
    ||typeof row.staged_change!=="boolean"||!(row.staged_limit===null||integer(row.staged_limit,1))
    ||!row.staged_change&&row.staged_limit!==null||!Array.isArray(row.queue)
    ||!row.queue.every(item=>integer(item?.id,1)&&["start","retry","restart","cancel"].includes(item.action)
      &&["project_limit","worker_unavailable","same_job","staged_change","dispatching"].includes(item.reason))
    ||!Array.isArray(row.waiting_runs)||!row.waiting_runs.every(item=>integer(item?.ticket_iid,1)&&["dispatching","worker_unavailable","project_limit","staged_change"].includes(item.reason))
    ||!Array.isArray(row.recent_operations)||!row.recent_operations.every(item=>integer(item?.id,1)&&actions.includes(item.action)
      &&["pending","running","succeeded","failed","uncertain"].includes(item.status)
      &&[item.reason,item.result].every(text=>typeof text==="string")))throw new ApiError("unexpected_response");
  return row;
}

/** Validate current status counts separately from historical operations and finished jobs. */
export function readCapacityOverview(value:unknown,project:string):CapacityOverview {
  const row=readCapacity(value,project) as CapacityOverview;
  if(typeof row.paused!=="boolean"||!row.job_counts||typeof row.job_counts!=="object"||Array.isArray(row.job_counts)
    ||Object.keys(row.job_counts).length!==currentJobStates.length
    ||!currentJobStates.every(status=>integer(row.job_counts[status])))throw new ApiError("unexpected_response");
  return row;
}

export const capacityCopy={
  en:{tab:"Capacity",jobStatus:"Current job status",noActiveJobs:"No active jobs"},
  fr:{tab:"Capacité",jobStatus:"État actuel des tâches",noActiveJobs:"Aucune tâche active"},
  de:{tab:"Kapazität",jobStatus:"Aktueller Auftragsstatus",noActiveJobs:"Keine aktiven Aufträge"},
  ro:{tab:"Capacitate",jobStatus:"Starea curentă a joburilor",noActiveJobs:"Niciun job activ"},
} satisfies Record<Locale,{tab:string;jobStatus:string;noActiveJobs:string}>;

export const workerCopy = {
 en:{capacity:"Project capacity",occupied:"Occupied",free:"Free",waiting:"Queued jobs",limit:"Parallel job limit",supervisor:"Supervisor",configuration:"Configuration worker",project:"Project worker",run:"Job worker",command:"Job control",recent:"Recent heartbeat",stale:"Late heartbeat",missing:"No heartbeat",busy:"Working",idle:"Idle",unknown:"Activity unknown",available:"Slot available",unavailable:"Admission unavailable",project_limit:"Project limit reached",staged_change:"Waiting for the staged lower limit",worker_unavailable:"Project worker unavailable",same_job:"Waiting for this job's current operation",dispatching:"Awaiting dispatch",staged:"Settings are staged; saved values remain unchanged.",stagedLower:"A lower job limit already holds new starts.",operations:"Your latest operations",pending:"Queued",running:"In progress",succeeded:"Confirmed",failed:"Failed",uncertain:"Result unconfirmed",start:"Start",retry:"Retry",restart:"Restart",cancel:"Cancel",configure:"Settings operation",pause:"Pause monitoring",resume:"Activate monitoring",delete:"Delete project",error:"Project status unavailable",workers:"Workers",heartbeatHelp:"Heartbeat shows contact; activity and free slots are separate.",retention:"Your draft could not be retained. Keep this page open or discard it.",corrupt:"The retained draft is unreadable. Discard changes to start fresh.",retained:"Unsaved values stay with this project in this browser tab."},
 fr:{capacity:"Capacité du projet",occupied:"Occupés",free:"Libres",waiting:"Tâches en file",limit:"Limite de tâches en parallèle",supervisor:"Superviseur",configuration:"Service de configuration",project:"Service du projet",run:"Service de tâche",command:"Contrôle des tâches",recent:"Contact récent",stale:"Contact en retard",missing:"Aucun contact",busy:"En activité",idle:"Inactif",unknown:"Activité inconnue",available:"Place disponible",unavailable:"Admission indisponible",project_limit:"Limite du projet atteinte",staged_change:"En attente de la limite réduite préparée",worker_unavailable:"Service du projet indisponible",same_job:"En attente de l’opération de cette tâche",dispatching:"En attente de lancement",staged:"Paramètres préparés ; les valeurs enregistrées restent inchangées.",stagedLower:"Une limite réduite retient déjà les nouveaux démarrages.",operations:"Vos dernières opérations",pending:"En file",running:"En cours",succeeded:"Confirmé",failed:"Échec",uncertain:"Résultat non confirmé",start:"Démarrer",retry:"Réessayer",restart:"Redémarrer",cancel:"Annuler",configure:"Opération de paramètres",pause:"Suspendre la surveillance",resume:"Activer la surveillance",delete:"Supprimer le projet",error:"État du projet indisponible",workers:"Services",heartbeatHelp:"Le contact, l’activité et les places libres sont distincts.",retention:"Votre brouillon n’a pas pu être conservé. Gardez cette page ouverte ou abandonnez-le.",corrupt:"Le brouillon conservé est illisible. Abandonnez les modifications pour recommencer.",retained:"Les valeurs non enregistrées restent dans cet onglet pour ce projet."},
 de:{capacity:"Projektkapazität",occupied:"Belegt",free:"Frei",waiting:"Aufträge in Warteschlange",limit:"Limit paralleler Aufträge",supervisor:"Supervisor",configuration:"Konfigurationsdienst",project:"Projektdienst",run:"Auftragsdienst",command:"Auftragssteuerung",recent:"Aktueller Kontakt",stale:"Verspäteter Kontakt",missing:"Kein Kontakt",busy:"Beschäftigt",idle:"Inaktiv",unknown:"Aktivität unbekannt",available:"Platz verfügbar",unavailable:"Aufnahme nicht verfügbar",project_limit:"Projektlimit erreicht",staged_change:"Wartet wegen des vorgemerkten kleineren Limits",worker_unavailable:"Projektdienst nicht verfügbar",same_job:"Wartet auf den laufenden Vorgang dieses Auftrags",dispatching:"Wartet auf Start",staged:"Einstellungen vorgemerkt; gespeicherte Werte bleiben unverändert.",stagedLower:"Ein kleineres Limit hält neue Starts bereits zurück.",operations:"Ihre letzten Vorgänge",pending:"Eingereiht",running:"In Bearbeitung",succeeded:"Bestätigt",failed:"Fehlgeschlagen",uncertain:"Ergebnis unbestätigt",start:"Starten",retry:"Wiederholen",restart:"Neu starten",cancel:"Abbrechen",configure:"Einstellungsvorgang",pause:"Überwachung pausieren",resume:"Überwachung aktivieren",delete:"Projekt löschen",error:"Projektstatus nicht verfügbar",workers:"Dienste",heartbeatHelp:"Kontakt, Aktivität und freie Plätze sind getrennte Angaben.",retention:"Der Entwurf konnte nicht gespeichert werden. Lassen Sie diese Seite offen oder verwerfen Sie ihn.",corrupt:"Der gespeicherte Entwurf ist unlesbar. Verwerfen Sie die Änderungen für einen Neustart.",retained:"Ungespeicherte Werte bleiben in diesem Browsertab bei diesem Projekt."},
 ro:{capacity:"Capacitatea proiectului",occupied:"Ocupate",free:"Libere",waiting:"Lucrări în coadă",limit:"Limita lucrărilor în paralel",supervisor:"Supervisor",configuration:"Worker de configurare",project:"Worker de proiect",run:"Worker de lucrare",command:"Controlul lucrărilor",recent:"Heartbeat recent",stale:"Heartbeat întârziat",missing:"Fără heartbeat",busy:"Lucrează",idle:"Inactiv",unknown:"Activitate necunoscută",available:"Loc disponibil",unavailable:"Preluare indisponibilă",project_limit:"Limita proiectului este atinsă",staged_change:"Așteaptă din cauza limitei reduse pregătite",worker_unavailable:"Workerul proiectului este indisponibil",same_job:"Așteaptă operația curentă a acestui job",dispatching:"Așteaptă lansarea",staged:"Setări pregătite; valorile salvate rămân neschimbate.",stagedLower:"O limită redusă oprește deja pornirile noi.",operations:"Ultimele tale operații",pending:"În coadă",running:"În desfășurare",succeeded:"Confirmat",failed:"Eșuat",uncertain:"Rezultat neconfirmat",start:"Pornește",retry:"Reîncearcă",restart:"Repornește",cancel:"Anulează",configure:"Operație de setări",pause:"Oprește monitorizarea",resume:"Activează monitorizarea",delete:"Șterge proiectul",error:"Starea proiectului este indisponibilă",workers:"Workeri",heartbeatHelp:"Heartbeat-ul arată contactul; activitatea și locurile libere sunt separate.",retention:"Draftul nu a putut fi păstrat. Ține pagina deschisă sau renunță la modificări.",corrupt:"Draftul păstrat nu poate fi citit. Renunță la modificări pentru a începe din nou.",retained:"Valorile nesalvate rămân la acest proiect în fila browserului."},
} satisfies Record<Locale,Record<string,string>>;
