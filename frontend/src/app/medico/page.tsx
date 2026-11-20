// @ts-nocheck
"use client";
import { useEffect, useRef, useState } from 'react';
import {
  Activity,
  CheckCircle2,
  CircleAlert,
  FileImage,
  ImagePlus,
  LoaderCircle,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from 'lucide-react';
import './medico.css';

// Production must use the same-origin Nginx proxy. A local .env value must
// never send a deployed browser to its own localhost.
const API_BASE = (process.env.NEXT_PUBLIC_MEDICO_API_URL || (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1' ? '/api' : 'http://127.0.0.1:8787/api')).replace(/\/$/, '');
const MAX_FILE_BYTES = 25 * 1024 * 1024;

function Medico() {
  const inputRef = useRef(null);
  const previewRef = useRef(null);
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [previewBox, setPreviewBox] = useState({ width: 0, height: 0 });
  const [naturalImageSize, setNaturalImageSize] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [service, setService] = useState({ loading: true, configured: false, model: '', detail: '' });

  useEffect(() => {
    if (!file) {
      setPreviewUrl('');
      setPreviewBox({ width: 0, height: 0 });
      setNaturalImageSize(null);
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    setNaturalImageSize(null);
    const container = previewRef.current;
    let observer;
    if (container) {
      const measure = () => setPreviewBox({ width: container.clientWidth, height: container.clientHeight });
      measure();
      if (typeof ResizeObserver !== 'undefined') {
        observer = new ResizeObserver(measure);
        observer.observe(container);
      }
    }
    return () => {
      URL.revokeObjectURL(url);
      observer?.disconnect();
    };
  }, [file]);

  useEffect(() => {
    document.title = 'Medico X-ray Screening';
    let active = true;
    fetch(API_BASE + '/medico/status')
      .then((response) => response.json().then((body) => {
        if (!response.ok) throw new Error(body.detail || 'Medico status unavailable');
        return body;
      }))
      .then((body) => {
        if (active) setService({
          loading: false,
          configured: Boolean(body.configured),
          model: body.model || '',
          detail: body.detail || '',
          modelUrl: body.modelUrl || '',
        });
      })
      .catch(() => {
        if (active) setService({ loading: false, configured: false, model: '', detail: 'Medico backend is unavailable. Start the local API server, then refresh this page.' });
      });
    return () => { active = false; };
  }, []);

  const chooseFile = (nextFile) => {
    if (!nextFile) return;
    const extension = nextFile.name.split('.').pop()?.toLowerCase();
    if (!['png', 'jpg', 'jpeg'].includes(extension)) {
      setFile(null);
      setResult(null);
      setError('X-ray uploads must be a PNG or JPEG image. PDF and DICOM files are not supported in this demo.');
      return;
    }
    if (nextFile.size > MAX_FILE_BYTES) {
      setFile(null);
      setResult(null);
      setError('The image must be 25 MB or smaller.');
      return;
    }
    setFile(nextFile);
    setResult(null);
    setError('');
  };

  const analyze = async () => {
    if (!file || busy) return;
    setError('');
    setResult(null);
    setBusy(true);
    const form = new FormData();
    form.append('document', file);
    try {
      const response = await fetch(API_BASE + '/medico/analyze', { method: 'POST', body: form });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body.detail === 'string' ? body.detail : 'The X-ray could not be analyzed.';
        throw new Error(detail);
      }
      setResult(body);
    } catch (requestError) {
      const message = requestError instanceof TypeError
        ? 'Could not reach the Medico backend. Start the local API server, then retry.'
        : requestError.message;
      setError(message || 'Could not reach the Medico API. Check that the backend is running.');
    } finally {
      setBusy(false);
    }
  };

  const removeFile = () => {
    setFile(null);
    setResult(null);
    setError('');
    if (inputRef.current) inputRef.current.value = '';
  };

  const imageFit = naturalImageSize && previewBox.width && previewBox.height
    ? (() => {
      const scale = Math.min(
        previewBox.width / naturalImageSize.width,
        previewBox.height / naturalImageSize.height,
      );
      return {
        width: naturalImageSize.width * scale,
        height: naturalImageSize.height * scale,
      };
    })()
    : null;
  const markedObservations = (result?.observations || [])
    .map((observation, index) => ({ observation, index }))
    .filter(({ observation }) => validRegion(observation.region));

  return (
    <div className="medico-app">
      <header className="medico-header">
        <div className="medico-brand" aria-label="Medico X-ray Screening">
          <span className="medico-brand-mark"><Activity size={19} /></span>
          <span><strong>Medico</strong><small>X-ray screening</small></span>
        </div>
        <div className="medico-header-right">
          <div className={'medico-service-state ' + (service.configured ? 'is-ready' : 'is-offline')}>
            <i />
            {service.loading ? 'Checking research model' : service.configured ? 'Model files available' : 'Model setup required'}
          </div>
        </div>
      </header>

      <main className="medico-main">
        <div className="medico-page-intro">
          <div>
            <p className="medico-eyebrow">FRACTURE SCREENING | RESEARCH</p>
            <h1>X-ray screening</h1>
            <p>Upload one musculoskeletal X-ray to screen for candidate fracture regions.</p>
          </div>
          <div className="medico-steps" aria-label="Review steps">
            <span className="is-current"><b>1</b> Image</span><i />
            <span className={result ? 'is-current' : ''}><b>2</b> Model screen</span><i />
            <span><b>3</b> Radiologist</span>
          </div>
        </div>

        <div className="medico-workflow-note">
          <ShieldCheck size={17} />
          <span><strong>Preliminary AI screening.</strong> A radiologist must review the image; this is not a diagnosis. Published model scope: hand, arm, leg, hip, and shoulder X-rays. Other body areas may produce unreliable results.</span>
        </div>

        <div className="medico-grid">
          <section className="medico-card medico-image-card">
            <div className="medico-card-heading">
              <div className="medico-heading-icon"><FileImage size={18} /></div>
              <div><p>STEP 1 Â· UPLOAD</p><h2>X-ray image</h2></div>
              {file && <button className="medico-clear-button" type="button" onClick={removeFile} disabled={busy}><X size={15} /> Remove</button>}
            </div>

            {!file ? (
              <div
                className={'medico-dropzone ' + (dragging ? 'is-dragging' : '')}
                onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setDragging(false); }}
                onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files?.[0]); }}
              >
                <div className="medico-upload-symbol"><ImagePlus size={23} /></div>
                <strong>Choose an X-ray image</strong>
                <span>Drop one PNG or JPEG here, or browse your device.</span>
                <small>Maximum 25 MB Â· X-ray images only Â· No PDF or DICOM in this demo</small>
                <button type="button" onClick={() => inputRef.current?.click()}><Upload size={15} /> Browse images</button>
              </div>
            ) : (
              <>
                <div className="medico-file-row">
                  <div className="medico-file-icon"><FileImage size={17} /></div>
                  <div className="medico-file-name"><strong>{file.name}</strong><small>{formatBytes(file.size)} Â· {file.type || 'Image file'}</small></div>
                  {result
                    ? <span className="medico-file-status"><CheckCircle2 size={14} /> Screened</span>
                    : <span className="medico-file-status is-pending">Ready</span>}
                </div>
                <div className="medico-preview" ref={previewRef}>
                  {previewUrl && (
                    <div
                      className="medico-image-stage"
                      style={imageFit ? { width: imageFit.width, height: imageFit.height } : { width: '100%', height: '100%' }}
                    >
                      <img
                        src={result?.analysisImage || previewUrl}
                        alt={result?.analysisImage ? 'Orientation-normalized X-ray sent for analysis' : 'Selected X-ray preview'}
                        onLoad={(event) => setNaturalImageSize({
                          width: event.currentTarget.naturalWidth,
                          height: event.currentTarget.naturalHeight,
                        })}
                      />
                      {result?.observations?.map((observation, index) => {
                        if (!validRegion(observation.region)) return null;
                        const region = displayRegion(observation.region);
                        return (
                          <div
                            className={'medico-region-marker is-' + (observation.kind || 'uncertain')}
                            key={'region-' + index}
                            style={{
                              left: (region.x / 10) + '%',
                              top: (region.y / 10) + '%',
                              width: (region.width / 10) + '%',
                              height: (region.height / 10) + '%',
                            }}
                            aria-label={'Research detector candidate region ' + regionLabel(index)}
                          >
                            <span>{regionLabel(index)}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                  <span className="medico-preview-label"><ScanLine size={13} /> {result?.analysisImage ? 'ANALYSIS IMAGE' : 'IMAGE PREVIEW'}</span>
                  {markedObservations.length > 0 && <span className="medico-overlay-note">APPROXIMATE REVIEW AREA | NOT A FRACTURE OUTLINE</span>}
                </div>
                <div className="medico-image-actions">
                  <button type="button" onClick={analyze} disabled={busy}>
                    {busy ? <><LoaderCircle className="medico-spinner" size={16} /> Reviewing imageâ€¦</> : <><Sparkles size={16} /> Analyze X-ray</>}
                  </button>
                </div>
              </>
            )}
            <input
              ref={inputRef}
              className="medico-hidden-input"
              type="file"
              accept=".png,.jpg,.jpeg,image/png,image/jpeg"
              onChange={(event) => { chooseFile(event.target.files?.[0]); event.target.value = ''; }}
              tabIndex="-1"
              aria-hidden="true"
            />
          </section>

          <section className="medico-card medico-results-card" aria-live="polite">
            <div className="medico-card-heading">
              <div className="medico-heading-icon is-ai"><Sparkles size={18} /></div>
              <div><p>STEP 2 | RESEARCH SCREEN</p><h2>Model output for review</h2></div>
            </div>
            {error && <div className="medico-error"><CircleAlert size={17} /><span>{error}</span></div>}
            {busy ? (
              <div className="medico-result-placeholder is-loading">
                <LoaderCircle className="medico-spinner" size={25} />
                <strong>Running fracture screening</strong>
                <span>The model loads its weights on the first request. A radiologist must review the original image.</span>
              </div>
            ) : result ? (
              <div className="medico-result-content">
                <div className="medico-impression">
                  <small>SUMMARY</small>
                  <p className="medico-summary-text">
                    {screeningSummaryParagraph(result, markedObservations)}
                  </p>
                </div>
              </div>
            ) : (
              <div className="medico-result-placeholder">
                <div className="medico-empty-icon"><ScanLine size={23} /></div>
                <strong>Your review will appear here</strong>
                <span>{service.detail || 'Upload one musculoskeletal X-ray, then select Analyze X-ray. The model does not verify modality or body part.'}</span>
                <div className="medico-empty-steps"><span><b>1</b> Image normalized</span><span><b>2</b> Research classifier and detector run</span><span><b>3</b> Radiologist reviews</span></div>
              </div>
            )}
          </section>
        </div>

        <footer className="medico-footer">
          <div><ShieldCheck size={15} /><span><strong>Use synthetic or de-identified demo images.</strong> Avoid uploading identifiable patient information.</span></div>
          <span>Research screening is not a diagnosis or treatment recommendation. A radiologist must interpret the image.</span>
        </footer>
      </main>
    </div>
  );
}

function formatBytes(bytes) {
  if (bytes < 1024 * 1024) return Math.max(1, Math.round(bytes / 1024)) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function validRegion(region) {
  return region && ['x', 'y', 'width', 'height'].every((key) => Number.isFinite(region[key]))
    && region.x >= 0 && region.y >= 0 && region.width > 0 && region.height > 0
    && region.x + region.width <= 1000.01 && region.y + region.height <= 1000.01;
}

function displayRegion(region) {
  // Add proportional context around every proposal: large proposals stay
  // larger than small ones. This is display padding, not fracture segmentation.
  const contextScale = 1.5;
  const width = Math.min(1000, region.width * contextScale);
  const height = Math.min(1000, region.height * contextScale);
  const x = Math.min(1000 - width, Math.max(0, region.x + region.width / 2 - width / 2));
  const y = Math.min(1000 - height, Math.max(0, region.y + region.height / 2 - height / 2));
  return { x, y, width, height };
}

function screeningSummaryParagraph(result, candidateRegions = []) {
  const regions = candidateRegions
    .map(({ observation, index }) => ({
      id: regionLabel(index),
      position: imagePosition(observation?.region),
    }))
    .filter(({ position }) => position);
  // Keep all returned review labels in the prose and the spatial description
  // short; the preview itself shows the exact candidate regions.
  const listedRegions = regions.slice(0, 2);
  const regionText = listedRegions
    .map(({ id, position }) => `${id} in the ${position}`)
    .join(' and ');
  const moreRegions = regions.length > listedRegions.length ? ' and other candidate areas' : '';

  if (result?.screening?.flagged === true) {
    const localization = regionText
      ? `It marked ${regionText}${moreRegions} as approximate areas to inspect; these boxes are search regions, not fracture outlines.`
      : 'The detector returned no usable review area, so the location cannot be specified.';
    return `The screening flagged this X-ray after detecting a possible fracture-related pattern. ${localization}`;
  }
  if (result?.screening?.flagged === false) {
    return 'The screening did not detect any fracture-related pattern. No candidate review area was found.';
  }
  return 'The screening did not return a result for this X-ray. Please retry when the service is available.';
}

function imagePosition(region) {
  if (!validRegion(region)) return '';
  const centerX = region.x + region.width / 2;
  const centerY = region.y + region.height / 2;
  const horizontal = centerX < 330 ? 'left' : centerX > 670 ? 'right' : 'center';
  const vertical = centerY < 330 ? 'upper' : centerY > 670 ? 'lower' : 'middle';
  if (vertical === 'middle' && horizontal === 'center') return 'center of the image';
  if (vertical === 'middle') return `middle-${horizontal} part of the image`;
  if (horizontal === 'center') return `${vertical}-center part of the image`;
  return `${vertical} ${horizontal} part of the image`;
}

function regionLabel(index) {
  return 'R-' + String(index + 1).padStart(2, '0');
}

export default Medico;

