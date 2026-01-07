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
		self._enabled = bool(api_key and self._model)
		self._client = None
		if self._enabled:
			try:
				from openai import OpenAI  # type: ignore
				self._client = OpenAI()
			except Exception:
				# Si no se puede inicializar, desactivar silenciosamente
				self._enabled = False

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
		asignaturas_txt = asignaturas.strip()
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
			"'{cargo}' encaja con {carrera}. {asig} {razon}.",
			"{carrera}: '{cargo}' muestra alineación con tu perfil. {asig} {razon}.",
			"Tu formación en {carrera} conecta naturalmente con '{cargo}'. {asig} {razon}.",
			"'{cargo}' es una oportunidad afín a {carrera}. {asig} {razon}."
		]
		idx = seed % len(templates)
		asig = f"Asignaturas: {asignaturas_txt}." if asignaturas_txt else ""
		razon = f"Refuerzan el encaje {pista_txt}." if pista_txt else ""
		line = templates[idx].format(cargo=cargo, carrera=carrera, asig=asig, razon=razon).strip()
		# Evitar puntos dobles o espacios redundantes
		line = re.sub(r"\s+", " ", line).strip()
		return line

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
					return msg
			except Exception:
				pass
		# Fallback determinístico
		return self._simple_explanation(
			cargo, descripcion, eurace_skills, skills, carrera, asignaturas, soft_skills
		)

	def personalize_batch(
		self,
		items: List[Dict[str, str]],
		carrera: str,
		asignaturas: str,
		soft_skills: List[int]
	) -> List[str]:
		if self._enabled and self._client is not None and items:
			try:
				prompt = self._build_batch_prompt(items, carrera, asignaturas, soft_skills)
				# Mayor variación de estilo y longitud controlada
				text = self._chat(prompt, temperature=0.5, presence_penalty=0.2, frequency_penalty=0.2, max_tokens=900)
				parsed = self._parse_batch_lines(text, expected=len(items))
				if parsed and len(parsed) == len(items):
					# Ensure each line is complete; replace suspiciously short/truncated lines with deterministic fallback
					final: List[str] = []
					for idx, it in enumerate(items):
						line = (parsed[idx] or '').strip()
						# Heuristic: consider truncated if very short or missing terminal punctuation
						is_short = len(line) < 80
						ends_ok = bool(re.search(r"[\.!?]$", line))
						if is_short or not ends_ok:
							final.append(
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
						else:
							final.append(line)
					return final
			except Exception:
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
		if self._enabled and self._client is not None and items:
			try:
				prompt = self._build_alt_batch_prompt(items, carrera, asignaturas, soft_skills)
				text = self._chat(prompt, temperature=0.5, presence_penalty=0.2, frequency_penalty=0.2, max_tokens=320)
				parsed = self._parse_batch_lines(text, expected=len(items))
				if parsed:
					return parsed
			except Exception:
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
			explicaciones.append(base + " " + extra)
		return explicaciones

	def soft_skills_advice(
		self,
		carrera: str,
		asignaturas: str,
		soft_skills: List[int]
	) -> str:
		# Si OpenAI está disponible, generar consejo personalizado (2–3 frases)
		if self._enabled and self._client is not None:
			try:
				prompt = (
					"Redacta un mensaje breve (2–3 frases) y personalizado para mostrar justo después del título 'Oportunidades si mejoras tus habilidades blandas'. "
					"No repitas el título, no uses markdown ni asteriscos. "
					"Incluye: (1) por qué reforzar 1–2 habilidades más bajas del usuario (no resaltes las que ya domina) es beneficioso (más ofertas, mejor remuneración o crecimiento); "
					"(2) reconoce 1 fortaleza si existe sin desviarte del foco; (3) sugiere 2 prácticas concretas. Sé directo, inspirador y sin ambigüedades.\n\n"
					f"Carrera: {carrera}\n"
					f"Asignaturas del usuario: {asignaturas}\n"
					f"Soft skills (1–5): {soft_skills}\n"
					f"Etiquetas soft: {self.SOFT_SKILLS_LABELS}\n"
				)
				msg = self._chat(prompt, temperature=0.4, presence_penalty=0.2, frequency_penalty=0.2, max_tokens=220)
				if msg:
					return msg
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
				{"role": "system", "content": "Eres un asistente que redacta en español, muy conciso (2–3 frases) y específico. Usa un tono profesional y claro."},
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
			"Genera una explicación breve (3–4 frases) y clara para mostrar en una tarjeta de trabajo. "
			"Incluye: 1) de qué va el cargo, 2) por qué encaja con el usuario usando asignaturas y EURACE, 3) menciona 1–2 skills técnicas explícitas de 'Skills técnicas' si existen. "
			"Evita repetir texto raro; sé específico y fácil de leer.\n\n"
			f"Cargo: {cargo}\n"
			f"Descripción (ruidosa): {descripcion}\n"
			f"EURACE_skills: {eurace_skills}\n"
			f"Skills técnicas: {skills}\n"
			f"Carrera del usuario: {carrera}\n"
			f"Asignaturas relevantes del usuario: {asignaturas}\n"
			f"Autoevaluación soft skills (1–5, 69–75): {soft_skills}\n"
		)

	def _build_batch_prompt(
		self,
		items: List[Dict[str, str]],
		carrera: str,
		asignaturas: str,
		soft_skills: List[int]
	) -> str:
		lines = [
			"Vas a producir una línea por oferta, en el formato 'N. mensaje'.",
			"Cada mensaje debe tener 3–4 frases y VARIAR el estilo entre ofertas (sin repetir la misma estructura).",
			"Incluye: 1) de qué va el rol, 2) por qué encaja con el usuario usando asignaturas y/o EURACE, 3) menciona 1–2 skills técnicas de 'Skills' si aportan contexto.",
			"Evita frases genéricas como 'refuerzan el encaje'; usa sinónimos y concreciones distintas por línea.",
			f"Carrera del usuario: {carrera}",
			f"Asignaturas relevantes del usuario: {asignaturas}",
			f"Soft skills (1–5): {soft_skills}",
			"\nOfertas:"
		]
		for i, it in enumerate(items, 1):
			lines.append(
				f"{i}) Cargo: {it.get('cargo','')}; Desc: {it.get('descripcion','')}; "
				f"EURACE: {it.get('eurace_skills','')}; Skills: {it.get('skills','')}"
			)
		lines.append(f"\nDevuelve exactamente {len(items)} líneas, una por oferta, en el formato 'N. mensaje'.")
		return "\n".join(lines)

	def _build_alt_batch_prompt(
		self,
		items: List[Dict[str, str]],
		carrera: str,
		asignaturas: str,
		soft_skills: List[int]
	) -> str:
		lines = [
			"Escribe una línea por oferta alternativa, formato 'N. mensaje'.",
			"Cada mensaje debe tener 2–3 frases y VARIAR el estilo entre ofertas (sin repetir la misma frase o estructura).",
			"Enfócate en 1–2 habilidades blandas que el usuario debe mejorar (no resaltes las que ya domina).",
			"Incluye: (1) resumen del cargo; (2) cómo reforzar esas habilidades mejora el encaje/proyección (más ofertas, mejor remuneración, crecimiento); (3) menciona 1–2 skills técnicas de 'Skills' si aportan contexto.",
			"Si solo hay 1 habilidad sugerida, usa forma singular (esta habilidad). Si hay 2, menciona ambas de forma natural (conectadas por 'y').",
			"Evita la frase 'esta oportunidad te ofrece mejores oportunidades a futuro' y sus variantes; usa sinónimos y paráfrasis.",
			f"Carrera del usuario: {carrera}",
			f"Asignaturas relevantes del usuario: {asignaturas}",
			f"Soft skills actuales (1–5): {soft_skills}",
			"\nOfertas alternativas (con 'suggest_soft'):" 
		]
		for i, it in enumerate(items, 1):
			lines.append(
				f"{i}) Cargo: {it.get('cargo','')}; Desc: {it.get('descripcion','')}; EURACE: {it.get('eurace_skills','')}; "
				f"Skills: {it.get('skills','')}; Sugeridas: {it.get('suggest_soft','')}"
			)
		lines.append(f"\nDevuelve exactamente {len(items)} líneas, una por oferta, en el formato 'N. mensaje'.")
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
			"Si fortaleces {obj}, podrás aspirar a responsabilidades más estratégicas y mejor remuneradas.",
			"Al incorporar {obj}, tu perfil ganará tracción para proyectos de mayor impacto y liderazgo.",
			"Con {obj}, mejorarás tu encaje y tendrás margen para negociar mejores condiciones.",
			"Al desarrollar {obj}, acelerarás tu crecimiento hacia posiciones de referencia en el área.",
			"Si potencias {obj}, destacarás en procesos selectivos con mayores exigencias técnicas y de gestión."
		]
		idx = seed % len(templates)
		if len(sugeridas) <= 1:
			obj = f"esta habilidad ({self._spanish_join(sugeridas)})" if sugeridas else "tus habilidades blandas prioritarias"
		else:
			obj = f"estas habilidades ({self._spanish_join(sugeridas[:2])})"
		extra = templates[idx].format(obj=obj)
		if tech_skills:
			extra += f" En paralelo, tus bases técnicas en {self._spanish_join(tech_skills)} harán que el salto sea tangible."
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
			if not p2 or p2.lower() == 'nan':
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
			toks = [t for t in re.split(r"\s+", st) if len(t) > 2 and t.lower() != 'nan' and re.search(r"[A-Za-zÁÉÍÓÚáéíóúñ]", t)]
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

