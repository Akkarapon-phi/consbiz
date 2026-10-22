# จัดตัดเหล็กเส้น 1 มิติ (cutting stock) ให้เหลือเศษน้อยที่สุด ใช้กับเหล็กทีละประเภท
#
# วิธี (sequential heuristic):
#   1. ทุกรอบ หารูปแบบการตัดที่ใช้เหล็ก 1 เส้นได้เต็มที่สุดของเหล็กแต่ละความยาวที่ยังมี (bounded knapsack)
#   2. เลือกรูปแบบที่เศษต่อความยาวเหล็กน้อยที่สุด แล้วตัดซ้ำได้หลายเส้นเท่าที่ชิ้นที่เหลือและสต็อกยังพอ
#   3. วนจนตัดครบทุกชิ้น
#   4. ลองซ้ำกับทุกชุดย่อยของความยาวเหล็ก (เช่น ใช้ทั้ง 10/12 ม., ใช้ 10 ม. อย่างเดียว) แล้วเลือกชุดที่ใช้เหล็กรวมน้อยสุด
#      เพราะการเลือกทีละรอบอาจใช้เหล็กยาวที่มีจำกัดหมดก่อน แล้วเหลือชิ้นที่ตัดได้ไม่คุ้ม
# knapsack ใช้ bitset ของ int ใน Python (บิตที่ i = ใช้ความยาว i มม. ได้) จึงแม่นระดับมิลลิเมตรและเร็ว
#
# หน่วยทั้งหมดเป็นมิลลิเมตร (int)

from collections import Counter
from itertools import combinations

# ลองทุกชุดย่อยเมื่อความยาวเหล็กไม่เกินค่านี้ (3 ความยาว = 7 ชุด)
MAX_SUBSET_LENGTHS = 3


class NotEnoughStock(Exception):
	pass


def plan_cuts(pieces, stocks, kerf=0):
	"""pieces: [(ความยาว, mark), ...] 1 รายการต่อ 1 ชิ้น
	stocks: [(ความยาวเหล็ก, จำนวนที่มี หรือ None = ไม่จำกัด), ...]
	คืน [{"stock": ความยาวเหล็ก, "bars": จำนวนเส้น, "cuts": [(ความยาว, จำนวนต่อเส้น, [marks])], "offcut": เศษต่อเส้น}]
	ValueError = มีชิ้นยาวกว่าเหล็กทุกความยาว, NotEnoughStock = เหล็กที่มีไม่พอ"""
	lengths = sorted({length for length, _ in stocks})
	subsets = [lengths]
	if len(lengths) <= MAX_SUBSET_LENGTHS:
		subsets = [list(c) for size in range(1, len(lengths) + 1) for c in combinations(lengths, size)]

	best = None
	error = None
	for subset in subsets:
		try:
			result = _plan(pieces, [s for s in stocks if s[0] in subset], kerf)
		except (ValueError, NotEnoughStock) as e:
			# แจ้งข้อผิดพลาดของชุดที่ใช้ทุกความยาว (ชุดย่อยล้มเหลวได้เพราะขาดความยาวบางแบบ)
			if subset == lengths:
				error = e
			continue
		score = (sum(p["stock"] * p["bars"] for p in result), sum(p["bars"] for p in result))
		if best is None or score < best[0]:
			best = (score, result)
	if best is None:
		raise error
	return best[1]


def _plan(pieces, stocks, kerf):
	marks = {}
	for length, mark in pieces:
		marks.setdefault(length, []).append(mark)
	remaining = {length: len(items) for length, items in marks.items()}

	available = {}
	for length, qty in stocks:
		if length in available and available[length] is None:
			continue
		available[length] = None if not qty else (available.get(length) or 0) + qty

	longest = max(available) if available else 0
	too_long = sorted(length for length in remaining if length > longest)
	if too_long:
		raise ValueError(too_long)

	patterns = []
	while any(remaining.values()):
		best = None
		for stock, left in sorted(available.items()):
			if left == 0:
				continue
			cut, used = best_fill(stock, remaining, kerf)
			if not cut:
				continue
			ratio = (stock - used) / stock
			if best is None or ratio < best[0] - 1e-12:
				best = (ratio, stock, cut, used)
		if best is None:
			raise NotEnoughStock({length: count for length, count in remaining.items() if count})

		_, stock, cut, used = best
		bars = min(remaining[length] // count for length, count in cut.items())
		if available[stock] is not None:
			bars = min(bars, available[stock])
			available[stock] -= bars
		cuts = []
		for length, count in sorted(cut.items(), reverse=True):
			remaining[length] -= count * bars
			taken = [marks[length].pop() for _ in range(count * bars)]
			cuts.append((length, count, sorted(set(taken), key=str)))
		patterns.append({"stock": stock, "bars": bars, "cuts": cuts, "offcut": max(stock - used, 0)})

	return merge_patterns(patterns)


def best_fill(stock, remaining, kerf):
	"""ชุดชิ้นที่รวมกันยาวที่สุดโดยไม่เกินเหล็ก 1 เส้น (แต่ละชิ้นกินรอยตัด kerf)
	คืน (Counter ความยาว -> จำนวน, ความยาวที่ใช้รวมรอยตัด)"""
	capacity = stock + kerf  # ชิ้นสุดท้ายไม่ต้องเผื่อรอยตัดหลังชิ้น
	items = []  # แตกจำนวนเป็นกลุ่ม 1, 2, 4, ... (binary splitting) ให้เป็น 0/1 knapsack
	for length, count in remaining.items():
		size = length + kerf
		if count <= 0 or size > capacity:
			continue
		limit = min(count, capacity // size)
		group = 1
		while limit > 0:
			take = min(group, limit)
			items.append((size * take, length, take))
			limit -= take
			group *= 2
	if not items:
		return Counter(), 0

	mask = (1 << (capacity + 1)) - 1
	reach = 1
	history = []
	for size, _, _ in items:
		history.append(reach)
		reach = (reach | (reach << size)) & mask

	best = reach.bit_length() - 1
	cut = Counter()
	total = best
	for i in range(len(items) - 1, -1, -1):
		if (history[i] >> total) & 1:
			continue
		size, length, take = items[i]
		cut[length] += take
		total -= size
	used = min(best, stock)
	return cut, used


def merge_patterns(patterns):
	"""รวมรูปแบบเดียวกัน (เหล็กยาวเท่ากันและตัดชิ้นเหมือนกัน) ที่เกิดจากหลายรอบ"""
	merged = {}
	for pattern in patterns:
		key = (pattern["stock"], tuple((length, count) for length, count, _ in pattern["cuts"]))
		if key in merged:
			target = merged[key]
			target["bars"] += pattern["bars"]
			for (_, _, marks), (_, _, more) in zip(target["cuts"], pattern["cuts"], strict=True):
				marks.extend(m for m in more if m not in marks)
		else:
			merged[key] = {
				**pattern,
				"cuts": [(length, count, list(marks)) for length, count, marks in pattern["cuts"]],
			}
	return sorted(merged.values(), key=lambda p: (p["stock"], p["offcut"]))
