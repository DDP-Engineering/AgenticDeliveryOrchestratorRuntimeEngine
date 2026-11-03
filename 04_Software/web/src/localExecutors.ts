/*
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
*/
export type Installation = {executable:string;entrypoint:string|null;command:string;source:string};
export type LocalExecutors = {system:string;machine:string;account:string;executors:{agent:string;installations:Installation[]}[]};
export const nativePresets:Record<string,string> = {
 pi:"pi -p --mode json --model {model} {prompt}",
};

/** A server path is a launch reference, never an uploaded browser file. */
export function validExecutablePath(value:string):boolean {
 return value.length>0 && value.length<=2048 && /^(?:[A-Za-z]:[\\/]|\/[^/])/.test(value)
  && !/[\u0000-\u001f"{}]/.test(value);
}

/** Rebuild the standard agent argv around an explicit native executable. */
export function commandForExecutable(agent:string,path:string):string {
 return validExecutablePath(path) && nativePresets[agent]
  ? '"'+path.replaceAll("\\","/")+'" '+nativePresets[agent].slice(agent.length+1) : "";
}

/** Show the current native path without interpreting a shell command. */
export function executableFromCommand(command:string):string {
 const first=/^\s*(?:"([^"]+)"|'([^']+)'|(\S+))/.exec(command);
 const path=first?.[1] ?? first?.[2] ?? first?.[3] ?? "";
 return validExecutablePath(path)?path:"";
}

/** Fail closed on malformed or oversized filesystem suggestions. */
export function validLocalExecutors(value:unknown):value is LocalExecutors {
 const item=value as LocalExecutors|null;
 const text=(s:unknown,max=4096):s is string=>typeof s==="string" && s.length<=max && !/[\u0000-\u001f]/.test(s);
 return !!item && ["Windows","Linux"].includes(item.system) && text(item.machine,255) && text(item.account,255)
  && Array.isArray(item.executors) && item.executors.length===1
  && new Set(item.executors.map(v=>v?.agent)).size===1
  && item.executors.every(v=>v && Object.hasOwn(nativePresets,v.agent) && Array.isArray(v.installations) && v.installations.length<=12
   && v.installations.every(i=>i && text(i.executable,2048) && validExecutablePath(i.executable)
    && (i.entrypoint===null || text(i.entrypoint,2048) && validExecutablePath(i.entrypoint))
    && text(i.command) && i.command.includes("{prompt}") && ["PATH","npm"].includes(i.source)));
}

/** Read host suggestions with a bounded wait; unavailable detection stays explicit. */
export async function readLocalExecutors():Promise<LocalExecutors|null> {
 try {
  const response=await fetch("/api/v1/local-executors",{credentials:"same-origin",cache:"no-store",signal:AbortSignal.timeout(10000)});
  const result:unknown=response.ok?await response.json():null;
  return validLocalExecutors(result)?result:null;
 } catch {return null;}
}

export const discoveryCopy = {
 en:{installed:"Detected installations",manual:"Manual command",path:"Executable path on the ADORE host",use:"Use executable",refresh:"Detect installed executors",loading:"Detecting installed executors…",unavailable:"Detection is unavailable. Open Advanced to enter an executable path or command.",missing:"No installation found for this agent. Open Advanced to enter its path or command.",host:"Execution host",help:"Choose an installation or enter its full executable path. On Windows use the real .exe; for Node agents edit the command with node.exe and the installed JavaScript entrypoint. Detection does not install tools or test model access.",command:"Executor launch command"},
 ro:{installed:"Instalări detectate",manual:"Comandă manuală",path:"Calea executabilului pe gazda ADORE",use:"Folosește executabilul",refresh:"Detectează executorii instalați",loading:"Se detectează executorii instalați…",unavailable:"Detectarea nu este disponibilă. Deschide Avansate pentru calea executabilului sau comandă.",missing:"Nu s-a găsit o instalare pentru acest agent. Deschide Avansate pentru cale sau comandă.",host:"Gazda execuției",help:"Alege o instalare sau introdu calea completă a executabilului. Pe Windows folosește fișierul .exe real; pentru agenții Node editează comanda cu node.exe și fișierul JavaScript instalat. Detectarea nu instalează unelte și nu testează accesul la model.",command:"Comanda de lansare a executorului"},
 fr:{installed:"Installations détectées",manual:"Commande manuelle",path:"Chemin de l’exécutable sur l’hôte ADORE",use:"Utiliser l’exécutable",refresh:"Détecter les exécuteurs installés",loading:"Détection des exécuteurs installés…",unavailable:"Détection indisponible. Ouvrez Avancé pour saisir le chemin de l’exécutable ou la commande.",missing:"Aucune installation pour cet agent. Ouvrez Avancé pour saisir le chemin ou la commande.",host:"Hôte d’exécution",help:"Choisissez une installation ou saisissez son chemin complet. Sous Windows utilisez le vrai .exe ; pour Node, indiquez node.exe et le fichier JavaScript installé dans la commande. La détection n’installe aucun outil et ne teste pas l’accès au modèle.",command:"Commande de lancement de l’exécuteur"},
 de:{installed:"Erkannte Installationen",manual:"Manueller Befehl",path:"Programmpfad auf dem ADORE-Rechner",use:"Programm verwenden",refresh:"Installierte Executoren erkennen",loading:"Installierte Executoren werden erkannt…",unavailable:"Erkennung nicht verfügbar. Unter Erweitert Programmpfad oder Befehl eingeben.",missing:"Keine Installation für diesen Agenten gefunden. Unter Erweitert Pfad oder Befehl eingeben.",host:"Ausführungsrechner",help:"Installation wählen oder vollständigen Programmpfad eingeben. Unter Windows die echte .exe verwenden; für Node node.exe und die installierte JavaScript-Datei im Befehl angeben. Die Erkennung installiert keine Werkzeuge und testet keinen Modellzugriff.",command:"Executor-Startbefehl"},
};
