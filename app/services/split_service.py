from typing import List, Dict, Any
from app.models.trip import Trip
from app.models.expense import Expense

class SplitService:
    @staticmethod
    def calculate_settlement(trip: Trip, expenses: List[Expense]) -> Dict[str, Any]:
        members = trip.members or []
        num_members = len(members)
        
        # Calculate total spent
        total_spent = sum(e.amount for e in expenses)
        total_budget = trip.total_budget if trip.trip_type == "packaged" else 0.0
        is_over_budget = False
        over_budget = 0.0
        remaining_budget = 0.0

        if trip.trip_type == "packaged":
            if total_spent > total_budget:
                is_over_budget = True
                over_budget = round(total_spent - total_budget, 2)
                remaining_budget = 0.0
            else:
                remaining_budget = round(total_budget - total_spent, 2)
        
        if num_members == 0:
            return {
                "trip_id": str(trip.id),
                "total_spent": round(total_spent, 2),
                "total_budget": round(total_budget, 2),
                "remaining_budget": round(remaining_budget, 2),
                "over_budget": over_budget,
                "is_over_budget": is_over_budget,
                "per_person": 0.0,
                "owes_summary": [],
                "settlements": [],
                "member_balances": {},
                "paid_by_member": {}
            }

        per_person = round(total_spent / num_members, 2)
        
        # Calculate how much each member has paid
        paid_by_member: Dict[str, float] = {m: 0.0 for m in members}
        for e in expenses:
            if e.paid_by in paid_by_member:
                paid_by_member[e.paid_by] += e.amount
            else:
                paid_by_member[e.paid_by] = e.amount
                members.append(e.paid_by)
                num_members = len(members)
                per_person = round(total_spent / num_members, 2)

        # Net balance: positive means they are owed money, negative means they owe money
        # balances = paid - per_person
        balances: Dict[str, float] = {}
        owes_summary: List[Dict[str, Any]] = []
        
        for m in members:
            net = round(paid_by_member.get(m, 0.0) - per_person, 2)
            balances[m] = net
            if net < -0.01:
                # Member owes money
                owes_summary.append({
                    "member": m,
                    "owes": abs(net),
                    "formatted": f"{m} owes ₹{abs(net):,.0f}"
                })

        # Calculate minimal debt settlements (Who pays whom)
        debtors = [[m, abs(bal)] for m, bal in balances.items() if bal < -0.01]
        creditors = [[m, bal] for m, bal in balances.items() if bal > 0.01]

        # Sort descending by amount
        debtors.sort(key=lambda x: x[1], reverse=True)
        creditors.sort(key=lambda x: x[1], reverse=True)

        settlements: List[Dict[str, Any]] = []
        d_idx = 0
        c_idx = 0

        while d_idx < len(debtors) and c_idx < len(creditors):
            debtor_name, debt_amt = debtors[d_idx]
            creditor_name, credit_amt = creditors[c_idx]

            transfer = round(min(debt_amt, credit_amt), 2)
            if transfer > 0:
                settlements.append({
                    "from_member": debtor_name,
                    "to_member": creditor_name,
                    "amount": transfer,
                    "formatted": f"{debtor_name} pays {creditor_name} ₹{transfer:,.0f}"
                })

            debtors[d_idx][1] -= transfer
            creditors[c_idx][1] -= transfer

            if debtors[d_idx][1] < 0.01:
                d_idx += 1
            if creditors[c_idx][1] < 0.01:
                c_idx += 1

        return {
            "trip_id": str(trip.id),
            "total_spent": round(total_spent, 2),
            "total_budget": round(total_budget, 2),
            "remaining_budget": round(remaining_budget, 2),
            "over_budget": over_budget,
            "is_over_budget": is_over_budget,
            "per_person": per_person,
            "owes_summary": owes_summary,
            "settlements": settlements,
            "member_balances": {m: round(b, 2) for m, b in balances.items()},
            "paid_by_member": {m: round(amt, 2) for m, amt in paid_by_member.items()}
        }

