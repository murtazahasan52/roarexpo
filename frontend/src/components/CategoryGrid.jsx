import Icon from "./Icon";
import { categoryIconMap } from "../categoryIcons";

export default function CategoryGrid({ categories }) {
  return (
    <div className="grid grid-4">
      {categories.map((cat) => (
        <div className="card category-card" key={cat.key}>
          <div className="icon-badge icon-badge-navy">
            <Icon name={categoryIconMap[cat.key] || "spark"} size={26} />
          </div>
          <div className="category-label">{cat.label}</div>
        </div>
      ))}
    </div>
  );
}
