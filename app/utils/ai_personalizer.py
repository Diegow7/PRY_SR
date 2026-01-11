"""AI Personalizer utility

Genera explicaciones y consejos personalizados. Por defecto funciona sin
llamadas externas (heurístico), pero si se configuran las variables de
entorno OPENAI_API_KEY y OPENAI_MODEL, usa la API de OpenAI para producir
resúmenes más naturales y contextuales.
"""
from typing import List, Dict, Optional
import os
import re
import json
import hashlib

try:
	from dotenv import load_dotenv  # type: ignore
	from pathlib import Path
	# Cargar .env desde la raíz del proyecto explícitamente
	root_env = Path(__file__).resolve().parents[2] / '.env'
	load_dotenv(dotenv_path=str(root_env))
except Exception:
	# Fallback a búsqueda por defecto
	try:
		load_dotenv()
	except Exception:
		pass


class AIPersonalizer:
	"""Generates concise explanations and soft-skills advice.

	Design goals:
	- Low latency: no network calls by default.
	- Deterministic: same inputs → same outputs.
	- Spanish output, 2–3 frases por explicación.
	"""

	SOFT_SKILLS_LABELS = [
		'Gestión',
		'Comunicación efectiva',
		'Liderazgo',
		'Trabajo en equipo',
		'Ética profesional',
		'Responsabilidad social',
		'Aprendizaje autónomo'
	]

	def __init__(self) -> None:
		# OpenAI support (enabled only if both API key and model are set)
		self._enabled = False
		self._model = os.getenv('OPENAI_MODEL', '').strip()
		api_key = os.getenv('OPENAI_API_KEY', '').strip()
		org_id = os.getenv('OPENAI_ORG_ID', '').strip()
		project_id = os.getenv('OPENAI_PROJECT', '').strip()
		base_url = os.getenv('OPENAI_BASE_URL', '').strip()
		self._require_llm = os.getenv('AI_PERSONALIZER_REQUIRE_LLM', '').strip().lower() in {'1','true','yes'}
		self._enabled = bool(api_key and self._model)
		self._client = None
		if self._enabled:
			try:
				from openai import OpenAI  # type: ignore
				# Inicializa el cliente usando explícitamente la API key y parámetros opcionales
				kwargs = { 'api_key': api_key }
				if org_id:
					kwargs['organization'] = org_id
				if project_id:
					kwargs['project'] = project_id
				if base_url:
					kwargs['base_url'] = base_url
				self._client = OpenAI(**kwargs)
			except Exception:
				# Si no se puede inicializar, desactivar silenciosamente
				self._enabled = False
		# Información de diagnóstico mínima para saber por qué no se usa LLM
		self._diag = {
			'enabled': self._enabled,
			'model': self._model,
			'require_llm': self._require_llm,
			'client_ready': self._client is not None
		}
		# Silenciar advertencias en consola; usar fallback determinístico si el LLM no está disponible

	def is_enabled(self) -> bool:
		"""Indica si el cliente de OpenAI está habilitado y listo."""
		return bool(self._enabled and self._client is not None)

	def status_details(self) -> Dict[str, bool | str]:
		"""Devuelve diagnóstico simple del estado del LLM."""
		return dict(self._diag)

	def _clean_subjects(self, asignaturas: str) -> str:
		"""Sanear asignaturas para evitar basura (ej. 'asdadsad'). Devuelve frase breve o ''"""
		s = (asignaturas or '').strip()
		if not s:
			return ''
		# Normalizar separadores y dividir
		parts = re.split(r"[;,]\s*|\s{2,}", s)
		clean: List[str] = []
		for p in parts:
			w = p.strip()
			if not w:
				continue
			# Heurísticas de sentido: contiene letras y vocales, baja puntuación, no 'nan'
			if self._normalize(w) in {'nan', 'null', 'none'}:
				continue
			if not re.search(r"[A-Za-zÁÉÍÓÚáéíóúñ]", w):
				continue
			if not re.search(r"[AEIOUaeiouáéíóú]", w):
				continue
			punct_ratio = (len(re.findall(r"[^\w\s]", w)) / max(len(w), 1))
			if punct_ratio > 0.35:
				continue
			# Evitar secuencias repetidas tipo 'aaaa', 'asdadsad' detectando baja diversidad
			diversidad = len(set([c for c in w.lower() if c.isalpha()]))
			if diversidad < 3 and len(w) > 4:
				continue
			clean.append(w)
		if not clean:
			return ''
		# Construir frase compacta (máx 3 elementos)
		return ", ".join(clean[:3])

	def _normalize(self, s: str) -> str:
		return re.sub(r"[^A-Za-zÁÉÍÓÚáéíóúñ]+", "", (s or "").lower())

	def _is_noise_token(self, s: str) -> bool:
		ns = self._normalize(s)
		if not ns:
			return True
		if ns in {"nan", "null", "none"}:
			return True
		if len(ns) <= 2:
			return True
		return False

	def _clean_text_out(self, text: str) -> str:
		t = (text or "").strip()
		if not t:
			return ""
		# eliminar tokens tipo 'nan', 'n/a', 'null', 'none' con puntuación o puntos de arrastre
		t = re.sub(r"(?i)\b(?:nan|n/?a|null|none)\b(?:\s*[\.…,;:\-]*)?", "", t)
		# colapsar puntuación repetida
		t = re.sub(r"[\.]{2,}", ".", t)
		# arreglar espacios antes de signos y dobles espacios
		t = re.sub(r"\s+", " ", t)
		t = re.sub(r"\s([\.!?,;:])", r"\1", t)
		# conectores huérfanos tras limpieza (e.g., ' y .')
		t = t.replace(" y .", ".")
		t = t.replace(" e .", ".")
		t = t.replace(" o .", ".")
		# limpiar comas/puntos mal formados
		t = t.replace(", .", ".")
		t = t.replace(" ,", ",")
		return t.strip()

	def _simple_explanation(
		self,
		cargo: str,
		descripcion: str,
		eurace_skills: str,
		skills: str,
		carrera: str,
		asignaturas: str,
		soft_skills: List[int]
	) -> str:
		# Generar un texto breve con variación determinística por oferta
		asignaturas_txt = self._clean_subjects(asignaturas)
		picked = self._pick_skills(skills)
		# Construir pistas sin 'nan' ni ruido
		use_eur = bool((eurace_skills or '').strip())
		pista_txt = ''
		if use_eur and picked:
			pista_txt = f"EURACE y {self._spanish_join(picked)}"
		elif picked:
			pista_txt = self._spanish_join(picked)
		elif use_eur:
			pista_txt = "las competencias EURACE del cargo"
		else:
			pista_txt = "tus competencias y trayectoria"

		seed_base = f"{cargo}|{carrera}|{asignaturas_txt}|{','.join(picked)}"
		seed = int(hashlib.md5(seed_base.encode('utf-8')).hexdigest(), 16)
		templates = [
			"'{cargo}' es pertinente para perfiles de {carrera}. {asig} {razon}.",
			"En {carrera}, '{cargo}' destaca como opción sólida. {asig} {razon}.",
			"La base de {carrera} sustenta '{cargo}' con buen potencial. {asig} {razon}.",
			"'{cargo}' guarda relación directa con {carrera}. {asig} {razon}."
		]
		idx = seed % len(templates)
		asig = f"Asignaturas relevantes: {asignaturas_txt}." if asignaturas_txt else ""
		razon = f"Se sustentan en {pista_txt}." if pista_txt else ""
		line = templates[idx].format(cargo=cargo, carrera=carrera, asig=asig, razon=razon).strip()
		# Evitar puntos dobles o espacios redundantes
		line = re.sub(r"\s+", " ", line).strip()
		line = self._clean_text_out(line)
		return line

	def _semantic_fallback(
		self,
		cargo: str,
		descripcion: str,
		eurace_skills: str,
		skills: str,
		carrera: str,
		asignaturas: str
	) -> str:
		parts = []

		if descripcion:
			parts.append(
				f"El rol de {cargo} se centra en actividades técnicas descritas en la oferta, "
				f"con responsabilidades alineadas al campo de {carrera.lower()}."
			)
		else:
			parts.append(
				f"El puesto de {cargo} se orienta a funciones propias del ámbito de {carrera.lower()}."
			)

		asign_txt = self._clean_subjects(asignaturas)
		if asign_txt:
			parts.append(
				f"La formación en asignaturas como {asign_txt} proporciona una base académica "
				f"útil para responder a las exigencias del puesto."
			)

		tech = self._pick_skills(skills)
		if tech:
			parts.append(
				f"A nivel técnico, se valoran conocimientos aplicados en {self._spanish_join(tech)}, "
				f"relevantes para el desempeño cotidiano del rol."
			)

		if eurace_skills.strip():
			parts.append(
				"El perfil también se alinea con competencias profesionales contempladas "
				"en el marco de referencia EURACE."
			)

		return self._clean_text_out(" ".join(parts[:3]))


	def personalize_description(
		self,
		cargo: str,
		descripcion: str,
		eurace_skills: str,
		skills: str,
		carrera: str,
		asignaturas: str,
		soft_skills: List[int]
	) -> str:
		# Si OpenAI está disponible, intentar explicación con LLM
		if self._enabled and self._client is not None:
			try:
				prompt = self._build_single_prompt(
					cargo, descripcion, eurace_skills, skills, carrera, asignaturas, soft_skills
				)
				msg = self._chat(prompt)
				if msg:
					return self._clean_text_out(msg)
			except Exception as e:
				# Log básico para diagnóstico en despliegue
				print(f"[AIPersonalizer] LLM error in personalize_description: {e}")
				pass
		# Fallback determinístico
		return self._semantic_fallback(
			cargo, descripcion, eurace_skills, skills, carrera, asignaturas
		)

	def personalize_batch(
		self,
		items: List[Dict[str, str]],
		carrera: str,
		asignaturas: str,
		soft_skills: List[int]
	) -> List[str]:
		# Si el LLM no está disponible, continuar con fallback determinístico sin mensajes de configuración
		if self._enabled and self._client is not None and items:
			try:
				prompt = self._build_batch_prompt(items, carrera, asignaturas, soft_skills)
				# Mayor variación de estilo y longitud controlada
				text = self._chat(
					prompt,
					temperature=0.7,
					presence_penalty=0.6,
					frequency_penalty=0.4,
					max_tokens=1100
				)
				parsed = self._parse_json_array(text, expected=len(items))
				if not parsed:
					parsed = self._parse_batch_lines(text, expected=len(items))
				if parsed and len(parsed) >= len(items):
					final: List[str] = []
					for idx, it in enumerate(items):
						line = (parsed[idx] or '').strip()
						# Limpieza y validación de calidad
						line = self._clean_text_out(line)
						is_short = len(line) < 80
						ends_ok = bool(re.search(r"[\.!?]$", line))
						if not ends_ok:
							line += "."
						if is_short:
							# Completar con una frase breve basada en skills si falta
							tech = self._pick_skills(it.get('skills',''))
							if tech:
								line += f" Destaca el uso de {self._spanish_join(tech)} en el puesto."
							else:
								line += f" Apoya el desarrollo del perfil de {carrera}."
						final.append(line)
					# Forzar diversidad básica si hay duplicados evidentes
					final = self._enforce_diversity(final, items, carrera)
					return final[:len(items)]
			except Exception as e:
				print(f"[AIPersonalizer] LLM error in personalize_batch: {e}")
				pass
		# Fallback determinístico
		explicaciones: List[str] = []
		for it in items:
			explicaciones.append(
				self._simple_explanation(
					cargo=it.get('cargo', ''),
					descripcion=it.get('descripcion', ''),
					eurace_skills=it.get('eurace_skills', ''),
					skills=it.get('skills', ''),
					carrera=carrera,
					asignaturas=asignaturas,
					soft_skills=soft_skills,
				)
			)
		return explicaciones

	def personalize_alt_batch(
		self,
		items: List[Dict[str, str]],
		carrera: str,
		asignaturas: str,
		soft_skills: List[int]
	) -> List[str]:
		# Si el LLM no está disponible, continuar con fallback determinístico
		if self._enabled and self._client is not None and items:
			try:
				prompt = self._build_alt_batch_prompt(items, carrera, asignaturas, soft_skills)
				text = self._chat(prompt, temperature=0.55, presence_penalty=0.25, frequency_penalty=0.25, max_tokens=450)
				parsed = self._parse_json_array(text, expected=len(items))
				if not parsed:
					parsed = self._parse_batch_lines(text, expected=len(items))
				if parsed:
					cleaned = [self._clean_text_out(p) for p in parsed]
					return self._enforce_diversity(cleaned, items, carrera)[:len(items)]
			except Exception as e:
				print(f"[AIPersonalizer] LLM error in personalize_alt_batch: {e}")
				pass
		explicaciones: List[str] = []
		for it in items:
			sugeridas = it.get('suggest_soft', '').strip()
			base = self._simple_explanation(
				cargo=it.get('cargo', ''),
				descripcion=it.get('descripcion', ''),
				eurace_skills=it.get('eurace_skills', ''),
				skills=it.get('skills', ''),
				carrera=carrera,
				asignaturas=asignaturas,
				soft_skills=soft_skills,
			)
			if sugeridas:
				ss = [s.strip() for s in sugeridas.split(',') if s.strip()]
				tech = self._pick_skills(it.get('skills',''))
				extra = self._alt_extra_phrase(it.get('cargo',''), ss, tech)
			else:
				tech = self._pick_skills(it.get('skills',''))
				extra = self._alt_extra_phrase(it.get('cargo',''), [], tech)
			explicaciones.append(self._clean_text_out(base + " " + extra))
		return explicaciones

	def soft_skills_advice(
		self,
		carrera: str,
		asignaturas: str,
		soft_skills: List[int]
	) -> str:
		# Si el LLM no está disponible, continuar con fallback determinístico
		# Si OpenAI está disponible, generar consejo personalizado (2–3 frases)
		if self._enabled and self._client is not None:
			try:
				prompt = (
					"Redacta un solo párrafo (2–3 frases), claro y personalizado, para mostrar tras el título 'Oportunidades si mejoras tus habilidades blandas'. "
					"NO repitas recomendaciones genéricas ni estructuras comunes. "
					"Conecta las habilidades blandas a reforzar con el tipo de cargos recomendados en esta consulta. "
					"Explica beneficios concretos (mayor responsabilidad, mejores condiciones, crecimiento profesional). "
					"Reconoce brevemente una fortaleza solo si aporta contexto real. "
					"Sugiere 2 acciones prácticas distintas en cada respuesta, vinculadas a la carrera y al entorno laboral implícito. "
					"Tono profesional, académico y no repetitivo.\n\n"
					"NO repitas el título ni comiences con 'Para impulsar'. Evita markdown. "
					"Incluye: (1) por qué reforzar 1–2 habilidades más bajas del usuario (no resaltes las más altas) genera beneficios concretos (más ofertas, mejor remuneración, crecimiento); "
					"(2) reconoce brevemente 1 fortaleza si existe; (3) sugiere 2 prácticas específicas y accionables relacionadas con la carrera/asignaturas. Tono profesional, variado y no genérico.\n\n"
					f"Carrera: {carrera}\n"
					f"Asignaturas (limpias si aplican): {self._clean_subjects(asignaturas)}\n"
					f"Puntajes de soft skills (1–5): {soft_skills}\n"
					f"Etiquetas soft: {self.SOFT_SKILLS_LABELS}\n"
				)
				msg = self._chat(prompt, temperature=0.5, presence_penalty=0.2, frequency_penalty=0.2, max_tokens=230)
				if msg:
					return self._clean_text_out(msg)
			except Exception:
				pass

		# Fallback: enfatiza 1–2 bajas, reconoce 1 fortaleza, da 2 prácticas + beneficio
		pares = list(zip(self.SOFT_SKILLS_LABELS, soft_skills))
		orden = sorted(pares, key=lambda x: x[1])
		bajas = [p[0] for p in orden if p[1] <= 3][:2]
		altas = [p[0] for p in pares if p[1] >= 4]
		fortaleza = altas[0] if altas else ''
		asign_txt = asignaturas.strip()
		beneficios = [
			"acceder a más ofertas relevantes",
			"mejorar tu proyección y remuneración",
			"acelerar tu crecimiento profesional"
		]
		benef = beneficios[(sum(soft_skills) % len(beneficios))]
		intro = f"Para impulsar tu trayectoria en {carrera}, prioriza "
		if bajas:
			intro += self._spanish_join(bajas)
		else:
			intro += "tus habilidades blandas clave"
		intro += f": te ayudará a {benef}."
		if fortaleza:
			intro += f" Ya destacas en {fortaleza}; capitalízalo mientras fortaleces lo anterior."
		acciones = "Prácticas rápidas: lidera pequeñas tareas en equipo y presenta avances breves; busca feedback quincenal y documenta aprendizajes."
		if asign_txt:
			acciones += f" Integra estas acciones con {asign_txt} para impacto inmediato."
		return intro + "\n" + acciones

	# -----------------
	# OpenAI utilities
	# -----------------
	def _chat(self, prompt: str, temperature: float = 0.2, presence_penalty: float = 0.0, frequency_penalty: float = 0.0, max_tokens: int = 250) -> str:
		from typing import Any
		if not (self._enabled and self._client):
			return ''
		resp = self._client.chat.completions.create(
			model=self._model,
			messages=[
				{"role": "system", "content": "Redacta en español, claro, directo y profesional. Entrega un único párrafo de 3–4 frases. Evita plantillas y frases hechas; PROHIBIDO usar expresiones como 'La base de ... sustenta', 'guarda relación directa', 'destaca como opción sólida', 'Asignaturas relevantes:'. Integra las asignaturas y EUR-ACE de forma natural si aportan. No uses la palabra 'encaja'. Varía el inicio y estructura. No incluyas tokens ruidosos como 'nan'."},
				{"role": "user", "content": prompt}
			],
			temperature=float(temperature),
			presence_penalty=float(presence_penalty),
			frequency_penalty=float(frequency_penalty),
			max_tokens=int(max_tokens)
		)
		return (resp.choices[0].message.content or '').strip()

	def _build_single_prompt(
		self,
		cargo: str,
		descripcion: str,
		eurace_skills: str,
		skills: str,
		carrera: str,
		asignaturas: str,
		soft_skills: List[int]
	) -> str:
		return (
			"Redacta un único párrafo de 3–4 frases para una tarjeta de trabajo, en tono profesional, claro y personalizado. "
			"Incluye: (1) un resumen conciso del rol; (2) una afirmación breve de afinidad razonada con la carrera del usuario (puedes usar variantes como 'presenta un buen nivel de afinidad' o similar, sin repetir exactamente entre ofertas), mencionando asignaturas válidas si aportan; (3) referencia a EUR-ACE solo si agrega valor; (4) 1–2 skills técnicas de la oferta únicamente si ayudan al contexto. "
			"PROHIBIDO: 'encaja/encaje', 'La base de ... sustenta', 'guarda relación directa', 'destaca como opción sólida', encabezados como 'Asignaturas relevantes:', y cualquier token ruidoso (p. ej., 'nan'). Varía el inicio y la estructura.\n\n"
			f"Cargo: {cargo}\n"
			f"Descripción (puede contener ruido): {descripcion}\n"
			f"EURACE (si aplica): {eurace_skills}\n"
			f"Skills técnicas de la oferta: {skills}\n"
			f"Carrera del usuario: {carrera}\n"
			f"Asignaturas del usuario (limpias si aplican): {self._clean_subjects(asignaturas)}\n"
			f"Soft skills (1–5): {soft_skills}\n"
		)

	def _build_batch_prompt(
		self,
		items: List[Dict[str, str]],
		carrera: str,
		asignaturas: str,
		soft_skills: List[int]
	) -> str:
		styles = [
			"analítico",
			"concreto",
			"académico",
			"orientado a impacto",
			"motivador",
			"estratégico",
		]
		lines = [
			"Genera EXACTAMENTE un arreglo JSON de cadenas (sin texto extra).",
			"Cada elemento es el mensaje para una oferta: 3–4 frases, tono profesional y ético.",
			"Varía el inicio y la estructura entre elementos; evita frases hechas o plantillas repetidas.",
			"REGLAS ESTRICTAS DE DIVERSIDAD:",
			"- Cada texto debe ser semánticamente distinto; no solo cambiar palabras.",
			"- Está PROHIBIDO reutilizar estructuras como: 'Asignaturas relevantes:', 'Se sustentan en', 'La base de ... sustenta', 'guarda relación directa', 'destaca como opción sólida'.",
			"- No repitas argumentos entre ofertas, aunque pertenezcan a la misma carrera.",
			"- Cada texto debe enfatizar UN enfoque distinto: operativo, académico, técnico, estratégico, o de proyección profesional.",
			"Incluye: (1) resumen del rol; (2) vínculo con la carrera del usuario con una afirmación breve de afinidad razonada usando asignaturas válidas y/o EUR-ACE; (3) 1–2 skills técnicas SOLO si aportan contexto real.",
			"Prohibido usar 'encaja/encaje'. No incluyas 'nan' ni cadenas sin sentido ni encabezados tipo 'Link:'.",
			f"Carrera del usuario: {carrera}",
			f"Asignaturas (limpias si aplican): {self._clean_subjects(asignaturas)}",
			f"Soft skills (1–5): {soft_skills}",
			"Para forzar diversidad, asigna estos estilos en orden (y repite si faltan): analítico, concreto, académico, orientado a impacto, motivador, estratégico.",
			"Ofertas:",
		]
		focus = [
			"operativo",
			"académico",
			"técnico",
			"estratégico",
			"proyección profesional"
		]

		for i, it in enumerate(items, 1):
			style = styles[(i - 1) % len(styles)]
			enfoque = focus[(i - 1) % len(focus)]
			lines.append(
				f"{i}) Cargo: {it.get('cargo','')}; "
				f"Desc: {it.get('descripcion','')}; "
				f"EURACE: {it.get('eurace_skills','')}; "
				f"Skills: {it.get('skills','')}; "
				f"Enfoque obligatorio: {enfoque}; "
				f"Estilo: {style}"
			)
		lines.append(f"Devuelve solo el arreglo JSON con {len(items)} elementos.")
		return "\n".join(lines)

	def _build_alt_batch_prompt(
		self,
		items: List[Dict[str, str]],
		carrera: str,
		asignaturas: str,
		soft_skills: List[int]
	) -> str:
		styles = [
			"analítico",
			"concreto",
			"académico",
			"orientado a impacto",
			"motivador",
			"estratégico",
		]
		lines = [
			"Genera EXACTAMENTE un arreglo JSON de cadenas (sin texto extra).",
			"Cada elemento: 2–3 frases. Varía inicio y estilo entre elementos.",
			"Enfócate en 1–2 habilidades blandas a mejorar (no resaltes las altas) y explica el beneficio (más ofertas, mejor remuneración, crecimiento).",
			"Incluye un breve resumen del cargo y 1–2 skills técnicas solo si aportan. Prohibido 'encaja/encaje' y tokens ruidosos.",
			f"Carrera del usuario: {carrera}",
			f"Asignaturas (limpias si aplican): {self._clean_subjects(asignaturas)}",
			f"Soft skills actuales (1–5): {soft_skills}",
			"Para diversidad, estilos sugeridos en orden: analítico, concreto, académico, orientado a impacto, motivador, estratégico.",
			"Ofertas:",
		]
		for i, it in enumerate(items, 1):
			style = styles[(i - 1) % len(styles)]
			lines.append(
				f"{i}) Cargo: {it.get('cargo','')}; Desc: {it.get('descripcion','')}; EURACE: {it.get('eurace_skills','')}; "
				f"Skills: {it.get('skills','')}; Sugeridas: {it.get('suggest_soft','')}; Estilo: {style}"
			)
		lines.append(f"Devuelve solo el arreglo JSON con {len(items)} elementos.")
		return "\n".join(lines)

	def _spanish_join(self, parts: List[str]) -> str:
		if not parts:
			return ''
		if len(parts) == 1:
			return parts[0]
		if len(parts) == 2:
			return f"{parts[0]} y {parts[1]}"
		return ", ".join(parts[:-1]) + f" y {parts[-1]}"

	def _alt_extra_phrase(self, cargo: str, sugeridas: List[str], tech_skills: List[str]) -> str:
		seed = int(hashlib.md5((cargo + '|' + ' '.join(sugeridas)).encode('utf-8')).hexdigest(), 16)
		templates = [
			"Si fortaleces {obj}, accederás a retos con mayor alcance y mejor proyección.",
			"Al incorporar {obj}, ganarás tracción hacia proyectos de impacto y liderazgo.",
			"Con {obj}, ampliarás tu margen para roles con mejores condiciones y responsabilidad.",
			"Al desarrollar {obj}, acelerarás tu avance hacia posiciones de referencia.",
			"Si potencias {obj}, destacarás en procesos con mayores exigencias técnicas y de gestión."
		]
		idx = seed % len(templates)
		if len(sugeridas) <= 1:
			obj = f"esta habilidad ({self._spanish_join(sugeridas)})" if sugeridas else "tus habilidades blandas prioritarias"
		else:
			obj = f"estas habilidades ({self._spanish_join(sugeridas[:2])})"
		extra = templates[idx].format(obj=obj)
		if tech_skills:
			extra += f" En paralelo, tus bases técnicas en {self._spanish_join(tech_skills)} consolidarán tu aporte en el rol."
		return extra

	def _pick_skills(self, skills_text: str) -> List[str]:
		st = (skills_text or '').strip()
		if not st:
			return []
		# Dividir por coma/; y limpiar
		parts = re.split(r"[;,]\s*", st)
		clean = []
		for p in parts:
			p2 = p.strip()
			# Evitar 'nan' o cadenas muy genéricas
			if not p2 or self._is_noise_token(p2):
				continue
			# Limitar longitud y caracteres extraños
			p2 = re.sub(r"\s+", " ", p2)
			if len(p2) > 40:
				continue
			# Requiere al menos una letra; evita tokens dominados por dígitos/puntuación
			if not re.search(r"[A-Za-zÁÉÍÓÚáéíóúñ]", p2):
				continue
			punct_ratio = (len(re.findall(r"[^\w\s]", p2)) / max(len(p2), 1))
			digit_ratio = (len(re.findall(r"\d", p2)) / max(len(p2), 1))
			if punct_ratio > 0.4 or digit_ratio > 0.4:
				continue
			clean.append(p2)
		if not clean:
			# fallback: separar por espacios y tomar tokens significativos
			toks = [t for t in re.split(r"\s+", st) if len(t) > 2 and not self._is_noise_token(t) and re.search(r"[A-Za-zÁÉÍÓÚáéíóúñ]", t)]
			clean = toks[:3]
		return clean[:2]

	def _parse_batch_lines(self, text: str, expected: int) -> List[str]:
		if not text:
			return []
		# Dividir por líneas que comiencen con índice o guión
		lines = [l.strip() for l in text.splitlines() if l.strip()]
		# Filtrar encabezados o texto extra
		cand: List[str] = []
		for l in lines:
			m = re.match(r"^(?:\d+\.|- )\s*(.+)$", l)
			cand.append(m.group(1).strip() if m else l)
		# Recortar a expected
		if len(cand) >= expected:
			return cand[:expected]
		return cand

	def _parse_json_array(self, text: str, expected: int) -> List[str]:
		try:
			data = json.loads(text)
			if isinstance(data, list):
				vals = [self._clean_text_out(str(x)) for x in data]
				if len(vals) >= expected:
					return vals[:expected]
				return vals
		except Exception:
			return []

	def _enforce_diversity(self, lines: List[str], items: List[Dict[str, str]], carrera: str) -> List[str]:
		seen: set = set()
		diverse: List[str] = []
		for idx, line in enumerate(lines):
			skel = re.sub(r"[^a-z0-9áéíóúñ]+", " ", line.lower()).strip()
			if skel in seen:
				# Añadir rasgo distintivo breve usando skills o EURACE
				tech = self._pick_skills(items[idx].get('skills', ''))
				if tech:
					addon = f" Además, el puesto valora {self._spanish_join(tech)}."
				elif items[idx].get('eurace_skills','').strip():
					addon = " Además, se alinean competencias EURACE del rol."
				else:
					addon = f" Relevante para perfiles de {carrera}."
				line = self._clean_text_out(line + addon)
			else:
				seen.add(skel)
			diverse.append(line)
		return diverse

