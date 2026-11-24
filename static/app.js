(() => {
  const items = document.getElementById("items");
  if (!items) return;
  const money = n => "₹" + (Number.isFinite(n) ? n : 0).toLocaleString("en-IN", {minimumFractionDigits:2, maximumFractionDigits:2});
  function recalc() {
    let subtotal = 0;
    items.querySelectorAll(".item-row").forEach(row => {
      const qty = Number(row.querySelector('[name="quantity[]"]').value || 0);
      const price = Number(row.querySelector('[name="unit_price[]"]').value || 0);
      const amount = Math.round(qty * price * 100) / 100;
      subtotal += amount;
      row.querySelector(".line-total").textContent = money(amount);
    });
    subtotal = Math.round(subtotal * 100) / 100;
    const rate = Math.min(100, Math.max(0, Number(document.getElementById("tax-rate").value || 0)));
    const tax = Math.round(subtotal * rate) / 100;
    document.getElementById("subtotal").textContent = money(subtotal);
    document.getElementById("tax-amount").textContent = money(tax);
    document.getElementById("grand-total").textContent = money(subtotal + tax);
  }
  function addRow() {
    const row = document.createElement("tr");
    row.className = "item-row";
    row.innerHTML = '<td><input name="description[]" required placeholder="Product or service"></td><td><input name="quantity[]" type="number" min="0.01" step="0.01" value="1" required></td><td><input name="unit_price[]" type="number" min="0" step="0.01" value="0" required></td><td class="line-total">₹0.00</td><td><button type="button" class="remove-row" aria-label="Remove item">×</button></td>';
    items.appendChild(row);
    recalc();
  }
  document.getElementById("add-row").addEventListener("click", addRow);
  items.addEventListener("input", recalc);
  items.addEventListener("click", e => {
    if (e.target.classList.contains("remove-row")) {
      if (items.querySelectorAll(".item-row").length > 1) e.target.closest("tr").remove();
      recalc();
    }
  });
  document.getElementById("tax-rate").addEventListener("input", recalc);
  recalc();
})();
