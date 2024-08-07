drop function mapmisstag;

DELIMITER //
create function mapmisstag(misstab varchar(50))
returns varchar(10) DETERMINISTIC
BEGIN
  declare result varchar(10);
  if strcmp(lower(misstab), 'BOTH') = 0 then
    set result = 'both';
  elseif strcmp(lower(misstab), 'unkn') = 0 then
    set result = 'Unkn';
  elseif strcmp(lower(misstab), 'None') = 0 then
    set result = 'none';
  else
    set result = misstab;
  end if;
  return result;
END//
DELIMITER ;

select mapmisstag('None');
select mapmisstag('AGFD');
select mapmisstag('UA');
select mapmisstag('BOTH');
select mapmisstag('unkn');
