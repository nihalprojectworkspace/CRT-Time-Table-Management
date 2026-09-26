const sidebar=document.querySelector('.sidebar');
const menu=document.querySelector('.mobile-menu');
function setSidebar(open){sidebar?.classList.toggle('open',open);document.querySelector('.sidebar-backdrop')?.classList.toggle('visible',open);menu?.setAttribute('aria-expanded',String(open));}
menu?.addEventListener('click',()=>setSidebar(!sidebar.classList.contains('open')));
document.querySelector('[data-close-sidebar]')?.addEventListener('click',()=>setSidebar(false));
document.addEventListener('keydown',event=>{if(event.key==='Escape')setSidebar(false)});
document.querySelectorAll('[data-confirm]').forEach(button=>button.addEventListener('click',event=>{if(!confirm(button.dataset.confirm))event.preventDefault()}));
document.querySelectorAll('form[method="post"]').forEach(form=>form.addEventListener('submit',()=>{
 const button=form.querySelector('button[type="submit"],button:not([type])');
 if(button){button.disabled=true;button.textContent='Saving…';if(form.action.includes('/generate'))button.textContent='Generating…';}
}));
document.querySelector('[data-view-select]')?.addEventListener('change',event=>{
 const form=event.target.form;form.querySelector('select[name="id"]').disabled=true;form.submit();
});
document.querySelectorAll('[data-assignment-form]').forEach(form=>{
 const course=form.querySelector('select[data-course]');
 const dependents=Array.from(form.querySelectorAll('[data-dependent]')).map(select=>({select,options:Array.from(select.options).slice(1)}));
 function filterResources(){
  const selected=course.value;
  const department=course.selectedOptions[0]?.dataset.department;
  const missing=[];
  dependents.forEach(({select,options})=>{
   const previous=select.value;
   select.replaceChildren(select.options[0]);
   options.filter(option=>selected&&(select.name==='teacher_id'?option.dataset.department===department:option.dataset.course===selected)).forEach(option=>select.add(option));
   select.value=Array.from(select.options).some(option=>option.value===previous)?previous:'';
   select.disabled=!selected||select.options.length===1;
   if(selected&&select.options.length===1)missing.push(select.name.replace('_id',''));
  });
  const hint=form.querySelector('[data-assignment-hint]');
  hint.textContent=!selected?'Choose a course to see its available teaching resources.':missing.length?'No matching '+missing.join(', ')+'. Add these records before creating an assignment.':'Showing classes and subjects for this course, and teachers in '+department+'.';
  const button=form.querySelector('button:not([type]),button[type="submit"]');
  if(button)button.disabled=!selected||missing.length>0;
 }
 course.addEventListener('change',filterResources);filterResources();
});
document.querySelector('[data-add-break]')?.addEventListener('click',()=>{
 const template=document.querySelector('#break-template');
 const list=document.querySelector('[data-break-list]');
 if(list.children.length>=12){alert('You can add up to 12 breaks per day.');return;}
 list.append(template.content.cloneNode(true));list.lastElementChild.querySelector('input').focus();
});
document.querySelector('[data-break-list]')?.addEventListener('click',event=>{
 const button=event.target.closest('[data-remove-break]');if(button)button.closest('.break-row').remove();
});
