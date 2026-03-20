# happy_friday_organizer.py

import pandas as pd
from fpdf import FPDF
import random
from collections import defaultdict
from itertools import combinations
import copy

class HappyFridayOrganizer:
    def __init__(self, girls_list, monthly_hosts_schedule):
        self.girls = sorted(list(set(girls_list)))  # Ensure unique girls and sorted for consistency
        self.monthly_hosts_schedule = monthly_hosts_schedule
        self.num_girls = len(self.girls)
        self.annual_pair_counts = defaultdict(int)
        self.monthly_assignments = []
        self.all_possible_pairs = self._generate_all_possible_pairs()

    def _generate_all_possible_pairs(self):
        pairs = set()
        for i in range(self.num_girls):
            for j in range(i + 1, self.num_girls):
                pairs.add(tuple(sorted((self.girls[i], self.girls[j]))))
        return list(pairs)

    def _get_current_pairs(self, group):
        current_pairs = set()
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                current_pairs.add(tuple(sorted((group[i], group[j]))))
        return list(current_pairs)

    def _calculate_girl_score_for_group(self, girl, current_group_members, current_month_pair_counts_snapshot):
        score = 0
        # Penalize based on repetitions with existing group members (including host)
        for member in current_group_members:
            pair = tuple(sorted((member, girl)))
            score += self.annual_pair_counts[pair] + current_month_pair_counts_snapshot[pair]
        return score

    def organize_year(self):
        for month_idx, hosts_of_month in enumerate(self.monthly_hosts_schedule):
            print(f"Organizando mes {month_idx + 1}...")
            # current_month_pair_counts_for_month will store the pair counts for the current month being organized
            current_month_pair_counts_for_month = defaultdict(int)
            
            # Attempt to organize the month using backtracking
            month_assignment_result, success = self._organize_month(
                hosts_of_month,
                current_month_pair_counts_for_month # This will be updated by the backtracking function if successful
            )
            
            if not success:
                print(f"No se pudo encontrar una asignación para el mes {month_idx + 1}. Considera ajustar el número de niñas o casas.")
                return False
            
            self.monthly_assignments.append(month_assignment_result)
            # Update annual pair counts with the successful month's counts
            for pair, count in current_month_pair_counts_for_month.items():
                self.annual_pair_counts[pair] += count
        return True

    def _organize_month(self, hosts_of_month, current_month_pair_counts_for_month):
        num_houses = len(hosts_of_month)
        available_girls_for_assignment = set(self.girls)
        month_assignment = {host: [host] for host in hosts_of_month}

        for host in hosts_of_month:
            if host in available_girls_for_assignment:
                available_girls_for_assignment.remove(host)
            else:
                print(f"Advertencia: La anfitriona {host} no está en la lista de niñas disponibles. Esto podría causar problemas.")
                return None, False

        # Determine target group sizes
        target_group_sizes = {}
        for host in hosts_of_month:
            target_group_sizes[host] = 4 # Default to 4 girls per group (host + 3 invited)

        # Adjust for cases where total girls don't fit perfectly
        num_invited_girls_total = self.num_girls - num_houses
        
        # Calculate how many groups will have 2 invited girls (total 3) instead of 3 invited girls (total 4)
        num_groups_size_3 = num_houses * 3 - num_invited_girls_total

        if num_groups_size_3 < 0: 
            print(f"Error: Demasiadas niñas ({self.num_girls}) para el número de casas anfitrionas ({num_houses}). No se pueden formar grupos de 3 o 4.")
            return None, False
        if num_groups_size_3 > num_houses: 
            print(f"Error: No hay suficientes niñas ({self.num_girls}) para llenar los grupos de {num_houses} casas. Se necesitan al menos {num_houses * 3} niñas en total.")
            return None, False

        hosts_for_size_3_groups = random.sample(hosts_of_month, num_groups_size_3)
        for host in hosts_for_size_3_groups:
            target_group_sizes[host] = 3

        # Backtracking algorithm to assign girls to groups
        def backtrack(current_host_idx, current_available_girls_pool, temp_current_month_pair_counts):
            if current_host_idx == num_houses:
                # All groups are filled, check if all girls are assigned
                if not current_available_girls_pool:
                    # If successful, copy the temporary pair counts to the main one for the month
                    current_month_pair_counts_for_month.update(temp_current_month_pair_counts)
                    return True
                return False

            host = hosts_of_month[current_host_idx]
            required_invited_girls = target_group_sizes[host] - 1

            if required_invited_girls == 0: 
                return backtrack(current_host_idx + 1, current_available_girls_pool, temp_current_month_pair_counts)

            # Recursive helper to find girls for the current group
            def find_girls_for_current_group(girls_to_pick, current_group_so_far, remaining_girls_pool):
                if girls_to_pick == 0:
                    # All required girls for this group have been picked.
                    # Update temporary pair counts for this group
                    for pair in self._get_current_pairs(current_group_so_far):
                        temp_current_month_pair_counts[pair] += 1
                    
                    # Try to backtrack for the next host
                    if backtrack(current_host_idx + 1, remaining_girls_pool, temp_current_month_pair_counts):
                        return True
                    
                    # If backtracking failed, revert temp_current_month_pair_counts for this group
                    for pair in self._get_current_pairs(current_group_so_far):
                        temp_current_month_pair_counts[pair] -= 1
                    return False

                # Sort remaining girls pool by score (least repetitions with current_group_so_far)
                scored_girls = []
                for girl in remaining_girls_pool:
                    score = self._calculate_girl_score_for_group(girl, current_group_so_far, temp_current_month_pair_counts)
                    scored_girls.append((score, girl))
                scored_girls.sort()

                for score, girl_to_add in scored_girls:
                    new_group_so_far = current_group_so_far + [girl_to_add]
                    new_remaining_girls_pool = remaining_girls_pool - {girl_to_add}
                    month_assignment[host].append(girl_to_add) # Add to the actual assignment

                    if find_girls_for_current_group(girls_to_pick - 1, new_group_so_far, new_remaining_girls_pool):
                        return True
                    
                    # Backtrack: remove the girl if this path didn't lead to a solution
                    month_assignment[host].pop()
                return False

            # Start finding girls for the current host's group
            initial_group_for_host = month_assignment[host][:] # Host is already in the group
            if find_girls_for_current_group(required_invited_girls, initial_group_for_host, current_available_girls_pool):
                return True
            return False

        # Initial call to backtrack
        # Pass a fresh defaultdict for temporary pair counts for the current month's attempt
        if backtrack(0, available_girls_for_assignment, defaultdict(int)):
            return month_assignment, True
        else:
            return None, False

    def generate_pdf_report(self, output_filename="happy_friday_report.pdf"):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt="Reporte Anual Happy Friday", ln=True, align="C")
        pdf.ln(10)

        for month_idx, assignment in enumerate(self.monthly_assignments):
            pdf.set_font("Arial", "B", size=12)
            pdf.cell(200, 10, txt=f"Mes {month_idx + 1}", ln=True, align="L")
            pdf.ln(5)

            # Prepare data for table
            table_data = [["Casa", "Niñas Invitadas"]]
            for host, group in assignment.items():
                invited_girls = [g for g in group if g != host]
                table_data.append([host, ", ".join(invited_girls)])
            
            # Calculate column widths dynamically
            col_width = pdf.w / 2.2 # Adjust as needed
            row_height = 10

            pdf.set_font("Arial", "B", size=10)
            for header in table_data[0]:
                pdf.cell(col_width, row_height, header, border=1, align="C")
            pdf.ln()

            pdf.set_font("Arial", size=10)
            for row in table_data[1:]:
                for item in row:
                    pdf.cell(col_width, row_height, item, border=1, align="L")
                pdf.ln()
            pdf.ln(10)

        # Ranking de Repeticiones
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Ranking de Repeticiones entre Pares de Niñas", ln=True, align="C")
        pdf.ln(10)

        if self.annual_pair_counts:
            sorted_pairs = sorted(self.annual_pair_counts.items(), key=lambda item: item[1], reverse=True)
            
            # Prepare data for ranking table
            ranking_table_data = [["Par de Niñas", "Veces Juntas"]]
            for pair, count in sorted_pairs:
                ranking_table_data.append([f"{pair[0]} y {pair[1]}", str(count)])

            # Calculate column widths dynamically
            col_width_pair = pdf.w / 2.5
            col_width_count = pdf.w / 5

            pdf.set_font("Arial", "B", size=10)
            pdf.cell(col_width_pair, row_height, ranking_table_data[0][0], border=1, align="C")
            pdf.cell(col_width_count, row_height, ranking_table_data[0][1], border=1, align="C")
            pdf.ln()

            pdf.set_font("Arial", size=10)
            for row in ranking_table_data[1:]:
                pdf.cell(col_width_pair, row_height, row[0], border=1, align="L")
                pdf.cell(col_width_count, row_height, row[1], border=1, align="C")
                pdf.ln()
        else:
            pdf.cell(200, 10, txt="No hay datos de repeticiones para mostrar.", ln=True, align="L")

        pdf.output(output_filename)
        print(f"Reporte PDF generado: {output_filename}")

# Example Usage (will be moved to a separate script later)
if __name__ == "__main__":
    # Dummy Data for testing
    all_girls = [f"Niña {i}" for i in range(1, 21)] # 20 girls
    
    monthly_hosts = []
    num_months = 12
    num_hosts_per_month = 5

    # Simple rotating host selection
    current_host_pool = list(all_girls)
    for _ in range(num_months):
        random.shuffle(current_host_pool)
        hosts_this_month = current_host_pool[:num_hosts_per_month]
        monthly_hosts.append(hosts_this_month)
        # Rotate the pool for next month to ensure everyone gets a chance to host
        current_host_pool = current_host_pool[num_hosts_per_month:] + current_host_pool[:num_hosts_per_month]

    # Create an instance of the organizer
    organizer = HappyFridayOrganizer(all_girls, monthly_hosts)

    # Organize the year and generate report
    if organizer.organize_year():
        organizer.generate_pdf_report()
    else:
        print("La organización anual no pudo completarse debido a problemas en la asignación mensual.")


