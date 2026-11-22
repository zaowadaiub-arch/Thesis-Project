                messagebox.showerror("Invalid percentage", "Discount and tax must be between 0 and 100.", parent=win); return
            total = subtotal * (1-d/100) * (1+t/100)
            now = datetime.now().isoformat(timespec="seconds")
            self.db.cursor.execute("INSERT INTO bills(order_id,subtotal,discount_pct,tax_pct,total,created_at) VALUES(?,?,?,?,?,?)", (order_id,subtotal,d,t,total,now))
            self.db.cursor.execute("UPDATE orders SET status='Billed' WHERE order_id=?", (order_id,))
            if table_no is not None: self.db.cursor.execute("UPDATE tables SET status='Free' WHERE table_no=?", (table_no,))
            self.db.conn.commit(); win.destroy()
            messagebox.showinfo("Invoice", f"CAFE SLICE\n\nOrder #{order_id}\nSubtotal: ${subtotal:.2f}\nDiscount ({d:g}%): -${subtotal*d/100:.2f}\nTax ({t:g}%): +${subtotal*(1-d/100)*t/100:.2f}\n\nTOTAL: ${total:.2f}\n\nThank you!")
            self.show_billing()
        self._button(win, "Create Invoice", save, True).grid(row=3, column=0, columnspan=2, pady=15)

    def show_inventory(self):
        self._clear("Inventory")
        self._heading("Inventory", "Track ingredients and keep an eye on low-stock items.")
        bar = tk.Frame(self.content, bg=self.BG); bar.pack(fill="x")
        self._button(bar, "＋ Add / Restock", self.add_stock, True).pack(side="left")
        self.inventory_tree = self._tree(self.content, ("name", "qty", "unit", "reorder", "status"),
                                         ("Ingredient", "Quantity", "Unit", "Reorder Level", "Stock Status"),
                                         (250, 120, 100, 150, 150))
        for name, qty, unit, reorder in self._rows("SELECT ingredient,quantity,unit,reorder_level FROM inventory ORDER BY ingredient"):
            status = "LOW STOCK" if qty <= reorder else "In stock"
            self.inventory_tree.insert("", "end", values=(name, f"{qty:g}", unit, f"{reorder:g}", status))

    def add_stock(self):
        win = tk.Toplevel(self.root); win.title("Add / Restock Inventory"); win.configure(bg=self.WHITE); win.transient(self.root); win.grab_set()
        fields = {}
        for i, label in enumerate(("Ingredient", "Quantity to add", "Unit (new item)", "Reorder level (new item)")):
            tk.Label(win, text=label, bg=self.WHITE).grid(row=i, column=0, padx=15, pady=7, sticky="w")
            ent = ttk.Entry(win, width=28); ent.grid(row=i, column=1, padx=15, pady=7); fields[label] = ent
        def save():
            name = fields["Ingredient"].get().strip()
            try:
                qty = float(fields["Quantity to add"].get())
                if not name or qty <= 0: raise ValueError
                row = self._rows("SELECT inv_id FROM inventory WHERE ingredient=?", (name,))
                if row:
                    self.db.cursor.execute("UPDATE inventory SET quantity=quantity+? WHERE ingredient=?", (qty,name))
                else:
                    unit = fields["Unit (new item)"].get().strip()
                    reorder = float(fields["Reorder level (new item)"].get())
                    if not unit or reorder < 0: raise ValueError
                    self.db.cursor.execute("INSERT INTO inventory(ingredient,quantity,unit,reorder_level) VALUES(?,?,?,?)", (name,qty,unit,reorder))
                self.db.conn.commit()
            except (ValueError, sqlite3.IntegrityError):
                messagebox.showerror("Invalid input", "Check the ingredient, positive quantity, unit, and reorder level.", parent=win); return
            win.destroy(); self.show_inventory()
        self._button(win, "Save Stock", save, True).grid(row=4, column=0, columnspan=2, pady=12)

    def show_employees(self):
        self._clear("Employees")
        self._heading("Employee Management", "Maintain staff details and monthly salary records.")
        bar = tk.Frame(self.content, bg=self.BG); bar.pack(fill="x")
        self._button(bar, "＋ Add Employee", self.add_employee, True).pack(side="left")
        self._button(bar, "Remove Selected", self.remove_employee).pack(side="left", padx=8)
        self.employee_tree = self._tree(self.content, ("id", "name", "role", "phone", "salary"),
                                        ("ID", "Employee Name", "Role", "Phone", "Monthly Salary"),
                                        (60, 230, 160, 170, 150))
        for row in self._rows("SELECT emp_id,name,role,phone,salary FROM employees ORDER BY emp_id"):
            self.employee_tree.insert("", "end", values=(row[0],row[1],row[2],row[3] or "-", f"${(row[4] or 0):.2f}"))

    def add_employee(self):
        win = tk.Toplevel(self.root); win.title("Add Employee"); win.configure(bg=self.WHITE); win.transient(self.root); win.grab_set()
        labels = ("Name", "Role", "Phone", "Monthly Salary")
        fields = {}
        for i, label in enumerate(labels):
            tk.Label(win, text=label, bg=self.WHITE).grid(row=i, column=0, padx=16, pady=8, sticky="w")
            ent = ttk.Entry(win, width=28); ent.grid(row=i, column=1, padx=16, pady=8); fields[label] = ent
        def save():
            try:
                name, role = fields["Name"].get().strip(), fields["Role"].get().strip()
                salary = float(fields["Monthly Salary"].get())
                if not name or not role or salary < 0: raise ValueError
            except ValueError:
                messagebox.showerror("Invalid input", "Enter a name, role, and valid salary.", parent=win); return
            self.db.cursor.execute("INSERT INTO employees(name,role,phone,salary) VALUES(?,?,?,?)", (name,role,fields["Phone"].get().strip(),salary))
            self.db.conn.commit(); win.destroy(); self.show_employees()
        self._button(win, "Save Employee", save, True).grid(row=4, column=0, columnspan=2, pady=14)

    def remove_employee(self):
        selected = self.employee_tree.selection()
        if not selected:
            messagebox.showinfo("Select employee", "Please select an employee first."); return
        emp_id = self.employee_tree.item(selected[0], "values")[0]
        if messagebox.askyesno("Confirm", "Remove this employee?"):
            self.db.cursor.execute("DELETE FROM employees WHERE emp_id=?", (emp_id,)); self.db.conn.commit(); self.show_employees()

    def show_reports(self):
        self._clear("Sales Reports")
        self._heading("Sales Reports", "A quick overview of sales performance and best-selling items.")
        total_bills, total_revenue = self._rows("SELECT COUNT(*),COALESCE(SUM(total),0) FROM bills")[0]
        today = datetime.now().strftime("%Y-%m-%d")
        today_bills, today_revenue = self._rows("SELECT COUNT(*),COALESCE(SUM(total),0) FROM bills WHERE created_at LIKE ?", (today+"%",))[0]
        summary = tk.Frame(self.content, bg=self.WHITE, padx=20, pady=16)
        summary.pack(fill="x")
        for label, value in [("Total Bills", total_bills), ("Total Revenue", f"${total_revenue:,.2f}"),
                             ("Today's Bills", today_bills), ("Today's Revenue", f"${today_revenue:,.2f}")]:
            cell = tk.Frame(summary, bg=self.WHITE); cell.pack(side="left", expand=True, fill="x")
            tk.Label(cell, text=label.upper(), bg=self.WHITE, fg=self.MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
            tk.Label(cell, text=str(value), bg=self.WHITE, fg=self.TEXT, font=("Segoe UI", 19, "bold")).pack(anchor="w", pady=6)
        tk.Label(self.content, text="Top Selling Items", bg=self.BG, fg=self.TEXT,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(22, 0))
        tree = self._tree(self.content, ("name", "qty", "revenue"),
                          ("Item", "Quantity Sold", "Revenue"), (330, 150, 150))
        for row in self._rows("""SELECT mi.name, SUM(oi.quantity), SUM(oi.quantity*oi.price_each)
                                 FROM order_items oi JOIN menu_items mi ON mi.item_id=oi.item_id
                                 GROUP BY mi.name ORDER BY SUM(oi.quantity) DESC LIMIT 10"""):
            tree.insert("", "end", values=(row[0], row[1], f"${row[2]:.2f}"))

    def close(self):
        try:
            self.db.close()
        finally:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = CafeSliceGUI(root)
    root.mainloop()
