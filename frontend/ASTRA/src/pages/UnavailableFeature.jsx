import { Construction, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

function UnavailableFeature({ title, description, requirement }) {
  return (
    <div className="pending-feature-page">
      <section className="pending-feature-card">
        <span className="pending-feature-icon"><Construction size={28} /></span>
        <span className="pending-feature-label">NOT CONNECTED IN PHASE 9A</span>
        <h1>{title}</h1>
        <p>{description}</p>
        <div className="pending-feature-requirement">
          <ShieldCheck size={18} />
          <span><strong>Required backend capability:</strong> {requirement}</span>
        </div>
        <Link to="/workbench">Open the supported text Workbench</Link>
      </section>
    </div>
  );
}

export default UnavailableFeature;
